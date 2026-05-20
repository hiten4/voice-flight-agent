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


while True:

    user_input = input("\nYou: ")

    extracted = extract_flight_info(user_input)

    state.update(extracted)

    missing = state.get_missing_fields()

    if missing:

        question = generate_question(missing[0])

        print("\nAssistant:", question)

        continue

    source = provider.search_airport(
        state.state["source"]
    )

    destination = provider.search_airport(
        state.state["destination"]
    )

    raw_flights = provider.search_flights(
        source_airport=source,
        destination_airport=destination,
        date=state.state["date"]
    )

    parsed = parse_flights(raw_flights)

    ranked = rank_flights(parsed)

    response = generate_flight_response(ranked)

    print("\nAssistant:\n")

    print(response)

    # Gujarati TTS
    speak_gujarati(response)

    break