"""
Voice Flight Agent — natural phone-call conversation model.

Architecture:
  ConversationStream runs a single always-on duplex audio stream.
  - Mic is always open; VAD detects utterances automatically.
  - TTS is interrupted the moment the user starts speaking.
  - on_utterance() is called with audio path whenever user finishes a sentence.
  - A Groq LLM (not slot-filling) decides what to say next in natural language.
"""

import sys
import os
import threading
import queue
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from app.stt.whisper_engine import transcribe_audio
from app.audio.conversation_stream import ConversationStream

try:
    from langdetect import detect as detect_lang
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

VOICE_MODE = len(sys.argv) > 1 and sys.argv[1] == "voice"

USE_MOCK = True

GREETING = (
    "Hello! I'm your flight assistant. "
    "Just tell me where you want to fly, your destination, and when — "
    "I'll find the best options for you."
)

EXIT_PHRASES = {"bye", "goodbye", "exit", "quit", "stop", "shut down"}

# ---------------------------------------------------------------------------
# LLM-driven conversation (Groq)
# ---------------------------------------------------------------------------

import json
from groq import Groq
import dateparser

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

def llm_respond(history: list) -> str:
    """Send conversation history to Groq and get the next response."""
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
            temperature=0.3,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[LLM] Error: {e}")
        return "Sorry, I had a connection issue. Could you repeat that?"


# ---------------------------------------------------------------------------
# Flight search
# ---------------------------------------------------------------------------

def do_flight_search(params: dict) -> str:
    """Run flight search and return a natural-language result string."""
    from app.flights.mock_provider import MockFlightProvider
    from app.flights.providers.skyscanner_provider import SkyScannerProvider
    from app.flights.parser import parse_flights
    from app.flights.ranker import rank_flights
    from app.response.response_generator import generate_flight_response_english

    provider = MockFlightProvider() if USE_MOCK else SkyScannerProvider()

    try:
        source      = provider.search_airport(params["source"])
        destination = provider.search_airport(params["destination"])

        if not source:
            return f"I couldn't find an airport for {params['source']}. Which city are you flying from?"
        if not destination:
            return f"I couldn't find an airport for {params['destination']}. Which city are you flying to?"

        raw = provider.search_flights(
            source_airport=source,
            destination_airport=destination,
            date=params["date"],
            passengers=params.get("passengers", 1),
            travel_class=params.get("travel_class", "economy"),
        )
        ranked = rank_flights(parse_flights(raw))
        return generate_flight_response_english(ranked)

    except Exception as e:
        print(f"[Search] Error: {e}")
        return "I had trouble searching for flights. Want to try again?"


# ---------------------------------------------------------------------------
# Main conversation loop
# ---------------------------------------------------------------------------

def run():
    if not VOICE_MODE:
        print("Text mode. Type messages, or 'quit' to exit.")
        _run_text_mode()
        return

    print("Voice mode active.")

    history        = []
    response_queue = queue.Queue()   # LLM responses waiting to be spoken
    lang           = "en"
    agent_busy     = threading.Event()  # set while agent is speaking

    def on_utterance(audio_path: str):
        """Called by ConversationStream when user finishes a sentence."""
        nonlocal lang

        text = transcribe_audio(audio_path).strip()
        if not text:
            return

        print(f"\nYou: {text}")

        # Detect language once
        if not history and LANGDETECT_AVAILABLE:
            try:
                lang = detect_lang(text)
            except Exception:
                lang = "en"

        history.append({"role": "user", "content": text})

        # Get LLM response
        response = llm_respond(history)
        print(f"Assistant (raw): {response}")

        # Check if LLM returned a JSON action
        clean = response.strip().lstrip("```json").rstrip("```").strip()
        try:
            action = json.loads(clean)

            if action.get("action") == "search":
                # Acknowledge immediately while searching
                stream.speak("Let me look that up for you.", lang=lang)
                result = do_flight_search(action)
                print(f"\n{result}")
                history.append({"role": "assistant", "content": result})
                stream.speak(result, lang=lang)
                stream.speak("Would you like to search for another flight?", lang=lang)

            elif action.get("action") == "exit":
                stream.speak("Goodbye! Have a great trip.", lang=lang)
                response_queue.put("__exit__")
                return

        except (json.JSONDecodeError, KeyError):
            # Plain conversational response
            history.append({"role": "assistant", "content": response})
            stream.speak(response, lang=lang)

    # Create and start the always-on stream
    stream = ConversationStream(on_utterance=on_utterance)
    stream.start()

    # Greet — not interruptible so user hears the full intro
    stream.speak(GREETING, lang="en", interruptible=False)
    stream.set_warmup(0.5)   # extra echo suppression after greeting

    print("Listening... (speak any time)")

    # Wait until exit signal
    try:
        while True:
            try:
                msg = response_queue.get(timeout=0.5)
                if msg == "__exit__":
                    break
            except queue.Empty:
                pass
    except KeyboardInterrupt:
        print("\nInterrupted.")
    finally:
        stream.stop()


# ---------------------------------------------------------------------------
# Text mode (for debugging without mic)
# ---------------------------------------------------------------------------

def _run_text_mode():
    history = []
    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not user_input:
            continue
        if user_input.lower() in EXIT_PHRASES:
            print("Goodbye!")
            break

        history.append({"role": "user", "content": user_input})
        response = llm_respond(history)

        clean = response.strip().lstrip("```json").rstrip("```").strip()
        try:
            action = json.loads(clean)
            if action.get("action") == "search":
                print("Assistant: Searching...")
                result = do_flight_search(action)
                print(f"\n{result}")
                history.append({"role": "assistant", "content": result})
                print("Assistant: Would you like to search for another flight?")
            elif action.get("action") == "exit":
                print("Assistant: Goodbye!")
                break
        except (json.JSONDecodeError, KeyError):
            print(f"Assistant: {response}")
            history.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    run()