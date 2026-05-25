import sys
from datetime import date

from app.llm.intent_extractor import extract_flight_info
from app.conversation.state_manager import ConversationState
from app.flights.providers.skyscanner_provider import SkyScannerProvider
from app.flights.mock_provider import MockFlightProvider

# ---------------------------------------------------------------
# Set USE_MOCK=True during development to avoid burning API calls
# Set USE_MOCK=False when testing against the real Skyscanner API
# ---------------------------------------------------------------
USE_MOCK = True
from app.flights.parser import parse_flights
from app.flights.ranker import rank_flights
from app.response.response_generator import generate_flight_response, generate_flight_response_english
from app.tts.gujarati_tts import speak
from app.conversation.question_generator import generate_question
from app.audio.recorder import record_audio
from app.stt.whisper_engine import transcribe_audio

try:
    from langdetect import detect as detect_lang
    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False

VOICE_MODE = len(sys.argv) > 1 and sys.argv[1] == "voice"

if VOICE_MODE:
    print("Voice mode active. The agent will speak and listen throughout.")
else:
    print("Text mode. Type your query, or 'quit' to exit.")

LANG = "en"

EXIT_WORDS = {"quit", "exit", "bye", "stop", "no", "n", "dont", "don't"}


def is_exit(text):
    import re
    # Strip punctuation so "Stop!" "No," "don't" all match correctly
    words = re.sub(r"[^\w\s]", "", text.lower()).split()
    return any(w in EXIT_WORDS for w in words)


def listen():
    print("Listening...")
    audio_path = record_audio()
    text = transcribe_audio(audio_path)
    print(f"You (transcribed): {text}")
    return text


def agent_say(text, lang=None):
    print(f"\nAssistant: {text}")
    if VOICE_MODE:
        try:
            speak(text, lang=lang or LANG)
        except Exception as e:
            print(f"(Voice output unavailable: {e})")


def get_input():
    if VOICE_MODE:
        return listen()
    return input("\nYou: ").strip()


def validate_date(date_str):
    try:
        return date.fromisoformat(date_str) >= date.today()
    except (ValueError, TypeError):
        return False


def detect_language(text):
    if not LANGDETECT_AVAILABLE:
        return "en"
    try:
        return detect_lang(text)
    except Exception:
        return "en"


def run_search():
    global LANG

    state = ConversationState()
    provider = MockFlightProvider() if USE_MOCK else SkyScannerProvider()
    history = []
    is_first_input = True

    while True:

        # --- Speak follow-up question before listening ---
        if not is_first_input:
            missing = state.get_missing_fields()
            if missing:
                question = generate_question(missing[0])
                agent_say(question)
                history.append({"role": "assistant", "content": question})

        # --- Get input ---
        try:
            user_input = get_input()
            is_first_input = False
        except Exception:
            agent_say("Could not capture input. Please try again.", lang="en")
            continue

        # --- Exit check at EVERY input point ---
        if is_exit(user_input):
            agent_say("Goodbye! Have a great trip.", lang="en")
            return False

        # --- Detect language once on first message ---
        if not history:
            LANG = detect_language(user_input)

        # --- Extract intent ---
        try:
            extracted = extract_flight_info(user_input, history=history)
        except Exception:
            agent_say("Sorry, I had trouble understanding that. Could you rephrase?", lang="en")
            continue

        history.append({"role": "user", "content": user_input})
        state.update(extracted)

        # --- Date validation ---
        if state.state.get("date") and not validate_date(state.state["date"]):
            msg = "That date is in the past. Please provide a future travel date."
            agent_say(msg, lang="en")
            state.clear_field("date")
            history.append({"role": "assistant", "content": msg})
            continue

        # --- Still missing fields? Loop back ---
        if state.get_missing_fields():
            continue

        # --- Airport search ---
        agent_say("Let me search for flights.", lang="en")

        try:
            source = provider.search_airport(state.state["source"])
        except Exception:
            agent_say("Could not connect to the flight service. Please try again.", lang="en")
            continue

        if not source:
            msg = f"I could not find an airport for {state.state['source']}. Try a different city name."
            agent_say(msg, lang="en")
            state.clear_field("source")
            history.append({"role": "assistant", "content": msg})
            continue

        try:
            destination = provider.search_airport(state.state["destination"])
        except Exception:
            agent_say("Could not connect to the flight service. Please try again.", lang="en")
            continue

        if not destination:
            msg = f"I could not find an airport for {state.state['destination']}. Try a different city name."
            agent_say(msg, lang="en")
            state.clear_field("destination")
            history.append({"role": "assistant", "content": msg})
            continue

        # --- Flight search ---
        passengers   = state.state.get("passengers") or 1
        travel_class = state.state.get("travel_class") or "economy"

        try:
            raw_flights = provider.search_flights(
                source_airport=source,
                destination_airport=destination,
                date=state.state["date"],
                passengers=passengers,
                travel_class=travel_class
            )
        except Exception:
            agent_say("Could not fetch flights. Please try again.", lang="en")
            continue

        # --- Parse and rank ---
        try:
            parsed = parse_flights(raw_flights)
            ranked = rank_flights(parsed)
        except Exception:
            agent_say("Unexpected response from service. Please try again.", lang="en")
            continue

        # --- Print English to terminal ---
        print("\n" + generate_flight_response_english(ranked))

        # --- Speak results in detected language ---
        if LANG == "gu":
            agent_say(generate_flight_response(ranked), lang="gu")
        else:
            agent_say(generate_flight_response_english(ranked), lang="en")

        # --- Post-result: ask to search again ---
        agent_say("Would you like to search for another flight? Say yes or no.", lang="en")

        try:
            again = get_input().lower()
        except Exception:
            return False

        # --- Exit check on post-result answer too ---
        if is_exit(again):
            agent_say("Goodbye! Have a great trip.", lang="en")
            return False

        if any(w in again for w in ("yes", "yeah", "sure", "haan", "ha", "હા")):
            agent_say("Sure! Tell me your next flight.", lang="en")
            return True
        else:
            agent_say("Goodbye! Have a great trip.", lang="en")
            return False


if __name__ == "__main__":
    while True:
        if not run_search():
            break