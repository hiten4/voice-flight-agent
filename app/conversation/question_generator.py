QUESTIONS = {
    "source": "Where are you travelling from?",
    "destination": "Where do you want to go?",
    "date": "When do you want to travel?",
    "passengers": "How many passengers?",
    "travel_class": "Which class do you prefer?"
}


def generate_question(missing_field):

    return QUESTIONS.get(
        missing_field,
        "Please provide more details."
    )