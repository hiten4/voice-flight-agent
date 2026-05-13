REQUIRED_FIELDS = [
    "source",
    "destination",
    "date",
    "passengers",
    "class"
]


def create_empty_state():

    return {
        "intent": None,
        "source": None,
        "destination": None,
        "date": None,
        "passengers": None,
        "class": None
    }


def update_state(current_state, extracted_data):

    for key, value in extracted_data.items():

        if value is not None:
            current_state[key] = value

    return current_state


def get_missing_fields(state):

    missing = []

    for field in REQUIRED_FIELDS:

        if state.get(field) is None:
            missing.append(field)

    return missing