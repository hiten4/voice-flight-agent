from app.llm.intent_extractor import extract_flight_info

from app.conversation.state_manager import ConversationState

from app.flights.providers.skyscanner_provider import SkyScannerProvider

from app.flights.parser import parse_flights

from app.flights.ranker import rank_flights

from app.response.response_generator import generate_flight_response

from app.tts.gujarati_tts import speak_gujarati

from app.conversation.question_generator import generate_question


state = ConversationState()

provider = SkyScannerProvider()

# Keeps the full conversation so the LLM understands short follow-up answers
history = []


while True:

    user_input = input("\nYou: ")

    # --- Step 1: Extract intent — pass full history for context ---
    try:
        extracted = extract_flight_info(user_input, history=history)
    except Exception as e:
        print("\nAssistant: Sorry, I had trouble understanding that. Could you rephrase?")
        continue

    # Record this user turn in history
    history.append({"role": "user", "content": user_input})

    state.update(extracted)

    missing = state.get_missing_fields()

    if missing:
        question = generate_question(missing[0])
        print("\nAssistant:", question)
        # Record the assistant's follow-up question in history too
        history.append({"role": "assistant", "content": question})
        continue

    # --- Step 2: Search for airports ---
    try:
        source = provider.search_airport(state.state["source"])
    except Exception as e:
        print("\nAssistant: I couldn't connect to the flight service. Please try again.")
        continue

    if not source:
        print(f"\nAssistant: I couldn't find an airport for '{state.state['source']}'. Could you try a different city name?")
        state.clear_field("source")
        continue

    try:
        destination = provider.search_airport(state.state["destination"])
    except Exception as e:
        print("\nAssistant: I couldn't connect to the flight service. Please try again.")
        continue

    if not destination:
        print(f"\nAssistant: I couldn't find an airport for '{state.state['destination']}'. Could you try a different city name?")
        state.clear_field("destination")
        continue

    # --- Step 3: Search for flights ---
    try:
        raw_flights = provider.search_flights(
            source_airport=source,
            destination_airport=destination,
            date=state.state["date"]
        )
    except Exception as e:
        print("\nAssistant: I had trouble fetching flights. Please try again in a moment.")
        continue

    # --- Step 4: Parse, rank, and respond ---
    try:
        parsed = parse_flights(raw_flights)
        ranked = rank_flights(parsed)
    except Exception as e:
        print("\nAssistant: I received an unexpected response from the flight service. Please try again.")
        continue

    response = generate_flight_response(ranked)

    print("\nAssistant:\n")
    print(response)

    # --- Step 5: Gujarati TTS ---
    try:
        speak_gujarati(response)
    except Exception as e:
        print("\n(Voice output unavailable)")

    break