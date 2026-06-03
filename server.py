"""
Flask server — bridges the ConversationStream backend with the HTML UI.

Endpoints:
  GET  /          → serve index.html
  GET  /status    → SSE stream of events (transcript, status changes)
  GET  /state     → JSON snapshot polled by Streamlit UI every 500 ms
  POST /stop      → gracefully stop the agent
"""

import sys
import os
import threading
import queue
import json
import datetime
from datetime import date
from flask import Flask, Response, jsonify, send_from_directory
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from app.stt.whisper_engine import transcribe_audio
from app.audio.conversation_stream import ConversationStream

try:
    from langdetect import detect as detect_lang
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

USE_MOCK = True

GREETING = (
    "Hello! I'm your flight assistant. "
    "Just tell me where you want to fly, your destination, and when — "
    "I'll find the best options for you."
)

# ---------------------------------------------------------------------------
# Event bus — pushes events to all SSE subscribers
# ---------------------------------------------------------------------------

_subscribers: list[queue.Queue] = []
_subscribers_lock = threading.Lock()


def push_event(event_type: str, data: dict):
    payload = json.dumps({"type": event_type, **data})
    with _subscribers_lock:
        dead = []
        for q in _subscribers:
            try:
                q.put_nowait(payload)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _subscribers.remove(q)


# ---------------------------------------------------------------------------
# LLM + flight search
# ---------------------------------------------------------------------------

import json as _json
from groq import Groq

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = f"""You are a friendly, natural-sounding flight assistant on a voice call.

Today is {date.today().strftime("%B %d, %Y")}.

Your job:
1. Understand what the user wants — even if they change their mind mid-sentence,
   correct themselves, or give partial information.
2. Ask only for what you still need (source, destination, date).
   Ask ONE question at a time in a conversational way.
3. When you have source, destination, and date, respond with ONLY this JSON:
   {{"action": "search", "source": "CityName", "destination": "CityName", "date": "YYYY-MM-DD", "passengers": 1, "travel_class": "economy"}}
4. If the user says bye/goodbye/exit, respond with ONLY: {{"action": "exit"}}
5. For everything else, respond with plain conversational text (no JSON).

Rules:
- Be concise — this is voice, not chat. One sentence per response.
- Never repeat what the user said back to them.
- If they say "no wait" or correct themselves, acknowledge and adapt immediately.
- Resolve relative dates: "tomorrow", "next Friday", etc. using today's date.
- Always use English city names.
"""


def llm_respond(hist):
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + hist,
            temperature=0.3,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return "Sorry, I had a connection issue. Could you repeat that?"


def do_flight_search(params):
    from app.flights.mock_provider import MockFlightProvider
    from app.flights.parser import parse_flights
    from app.flights.ranker import rank_flights
    from app.response.response_generator import generate_flight_response_english

    provider = MockFlightProvider()
    try:
        source      = provider.search_airport(params["source"])
        destination = provider.search_airport(params["destination"])
        if not source:
            return f"I couldn't find an airport for {params['source']}. Which city are you flying from?", []
        if not destination:
            return f"I couldn't find an airport for {params['destination']}. Which city are you flying to?", []
        raw    = provider.search_flights(
            source_airport=source, destination_airport=destination,
            date=params["date"], passengers=params.get("passengers", 1),
            travel_class=params.get("travel_class", "economy"),
        )
        ranked = rank_flights(parse_flights(raw))
        # ranked is a list of flight dicts — return both the text response and raw list
        text = generate_flight_response_english(ranked)
        return text, ranked
    except Exception:
        return "I had trouble searching for flights. Want to try again?", []


# ---------------------------------------------------------------------------
# Shared conversation state (read by /state endpoint)
# ---------------------------------------------------------------------------

history            = []          # [{"role": "user"|"assistant", "content": str, "ts": str}]
history_lock       = threading.Lock()
current_status     = "stopped"   # updated throughout on_utterance / start_agent
latest_flights     = []          # updated after every successful flight search
session_start_time = datetime.datetime.now()
_stream: ConversationStream | None = None
_stop_event        = threading.Event()


def _ts() -> str:
    return datetime.datetime.now().strftime("%H:%M")


def _set_status(state: str):
    global current_status
    current_status = state
    push_event("status", {"state": state})


# ---------------------------------------------------------------------------
# Utterance handler
# ---------------------------------------------------------------------------

# Whisper commonly hallucinates these strings on silence / background noise.
# Any transcript that matches is silently dropped before hitting the LLM.
_NOISE_PATTERNS = [
    r"^[.,!?\s]+$",
    r"^(uh+|um+|mm+|hmm+|ah+|oh+)$",
    r"^thank you[.!]?$",
    r"^thanks[.!]?$",
    r"^you$", r"^the$", r"^a$",
    r"^\[.*\]$",
    r"^\(.*\)$",
    r"^subtitles? by",
]
import re as _re
_NOISE_RE = _re.compile(
    "|".join(_NOISE_PATTERNS), _re.IGNORECASE
)

def _is_noise(text: str) -> bool:
    """Return True if the transcript looks like background noise, not real speech."""
    stripped = text.strip()
    # Too short — Whisper often outputs 1-2 char garbage on silence
    if len(stripped) < 3:
        return True
    # Only 1 word and it's very short — likely a noise artifact
    words = stripped.split()
    if len(words) == 1 and len(words[0]) <= 3:
        return True
    if _NOISE_RE.match(stripped):
        return True
    return False


def on_utterance(audio_path: str):
    global latest_flights

    text = transcribe_audio(audio_path).strip()
    if not text:
        return

    if _is_noise(text):
        print(f"[on_utterance] dropped noise transcript: {text!r}")
        return

    push_event("user", {"text": text})

    lang = "en"
    if LANGDETECT_AVAILABLE:
        try:
            lang = detect_lang(text)
        except Exception:
            pass

    with history_lock:
        history.append({"role": "user", "content": text, "ts": _ts()})
        hist_copy = list(history)

    _set_status("thinking")
    response = llm_respond([{"role": m["role"], "content": m["content"]} for m in hist_copy])

    import re as _re
    clean = _re.sub(r'```(?:json)?', '', response).strip()
    try:
        action = _json.loads(clean)

        if action.get("action") == "search":
            ack = "Let me look that up for you."
            push_event("agent", {"text": ack})
            _set_status("speaking")
            _stream.speak(ack, lang=lang)

            _set_status("searching")
            result_text, flights = do_flight_search(action)

            latest_flights = flights
            if flights:
                push_event("flights", {"flights": flights})

            with history_lock:
                history.append({"role": "assistant", "content": result_text, "ts": _ts()})

            push_event("agent", {"text": result_text})
            _set_status("speaking")
            _stream.speak(result_text, lang=lang)

            followup = "Would you like to search for another flight?"
            push_event("agent", {"text": followup})
            with history_lock:
                history.append({"role": "assistant", "content": followup, "ts": _ts()})
            _stream.speak(followup, lang=lang)
            _set_status("listening")

        elif action.get("action") == "exit":
            bye = "Goodbye! Have a great trip."
            push_event("agent", {"text": bye})
            _set_status("speaking")
            _stream.speak(bye, lang=lang)
            _set_status("stopped")
            _stop_event.set()

    except (_json.JSONDecodeError, KeyError):
        with history_lock:
            history.append({"role": "assistant", "content": response, "ts": _ts()})
        push_event("agent", {"text": response})
        _set_status("speaking")
        _stream.speak(response, lang=lang)
        _set_status("listening")


# ---------------------------------------------------------------------------
# Agent bootstrap
# ---------------------------------------------------------------------------

def start_agent():
    global _stream, session_start_time
    session_start_time = datetime.datetime.now()

    # Clean up any previous stream
    if _stream is not None:
        try:
            _stream.stop()
        except Exception:
            pass

    try:
        _stream = ConversationStream(on_utterance=on_utterance)
        _stream.start()
        _set_status("speaking")
        _stream.speak(GREETING, lang="en", interruptible=False)
        _stream.set_warmup(0.5)
        _set_status("listening")
        _stop_event.wait()
        _stream.stop()
    except Exception as e:
        print(f"[start_agent] error: {e}")
        _set_status("stopped")


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder="static")

# Allow Streamlit (port 8501) and any local origin to poll /state and /stop
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/status")
def status_stream():
    """SSE endpoint — pushes events to the browser HTML UI."""
    q: queue.Queue = queue.Queue(maxsize=50)
    with _subscribers_lock:
        _subscribers.append(q)

    def generate():
        yield f"data: {json.dumps({'type': 'status', 'state': 'listening'})}\n\n"
        while True:
            try:
                payload = q.get(timeout=20)
                yield f"data: {payload}\n\n"
            except queue.Empty:
                yield ": heartbeat\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/state")
def get_state():
    """JSON snapshot polled by the Streamlit UI every 500 ms."""
    with history_lock:
        hist_copy = list(history)

    formatted = []
    for m in hist_copy:
        role = m.get("role", "assistant")
        formatted.append({
            "role": "user" if role == "user" else "agent",
            "text": m.get("content", m.get("text", "")),
            "ts":   m.get("ts", ""),
        })

    return jsonify({
        "status":        current_status,
        "history":       formatted,
        "flights":       latest_flights,
        "session_start": session_start_time.strftime("%H:%M:%S"),
        "turn_count":    len([m for m in hist_copy if m.get("role") == "user"]),
    })


@app.route("/stop", methods=["POST"])
def stop():
    """Gracefully stop the agent (called by both HTML UI and Streamlit UI)."""
    global current_status, _stop_event
    _stop_event.set()
    current_status = "stopped"
    push_event("status", {"state": "stopped"})
    _stop_event = threading.Event()  # reset so /start works cleanly
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@app.route("/start", methods=["POST"])
def start():
    """Start (or restart) the agent session — called by the UI."""
    global _stop_event, history, latest_flights, current_status
    # Always start from a clean event (stop may have replaced the old one)
    _stop_event = threading.Event()
    with history_lock:
        history.clear()
    latest_flights = []
    current_status = "stopped"
    t = threading.Thread(target=start_agent, daemon=True)
    t.start()
    return jsonify({"ok": True})


@app.route("/health")
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Do NOT auto-start the agent here.
    # The UI calls POST /start when the user clicks "Start Session".
    # This ensures Flask is fully up and SSE subscribers are connected
    # before any audio/speech begins.
    print("Flask server ready — open http://localhost:5000")
    print("The agent will start when you click 'Start Session' in the UI.")
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)