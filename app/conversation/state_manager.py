REQUIRED_FIELDS = [
    "source",
    "destination",
    "date"
]


class ConversationState:

    def __init__(self):

        self.state = {
            "intent": None,
            "source": None,
            "destination": None,
            "date": None,
            "passengers": None,
            "travel_class": None
        }

    def update(self, extracted_data: dict):

        for key, value in extracted_data.items():

            if value is not None:
                self.state[key] = value

    def clear_field(self, field: str):
        """Reset a single field back to None so the agent asks for it again."""

        if field in self.state:
            self.state[field] = None

    def get_missing_fields(self):

        missing = []

        for field in REQUIRED_FIELDS:

            if not self.state.get(field):
                missing.append(field)

        return missing

    def is_complete(self):

        return len(self.get_missing_fields()) == 0

    def get_state(self):

        return self.state
