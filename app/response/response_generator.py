def _stops_label_gujarati(stops):
    if stops == 0:
        return "સીધી ફ્લાઇટ"    # Direct flight
    elif stops == 1:
        return "1 સ્ટોપ"
    else:
        return f"{stops} સ્ટોપ"


def _stops_label_english(stops):
    if stops == 0:
        return "Direct"
    elif stops == 1:
        return "1 stop"
    else:
        return f"{stops} stops"


def generate_flight_response(flights):
    """
    Generates the response text in Gujarati.
    This is what gets passed to the TTS engine.
    """

    if not flights:
        return "માફ કરશો, કોઈ ફ્લાઇટ મળી નથી."

    top_flights = flights[:3]

    lines = [f"મને {len(top_flights)} ફ્લાઇટ વિકલ્પો મળ્યા.\n"]

    for index, flight in enumerate(top_flights, start=1):

        stops  = _stops_label_gujarati(flight.get("stops", 0))
        price    = int(flight["price"])
        duration = flight["duration_minutes"]
        airline  = flight["airline"]
        departure = flight["departure"]
        arrival   = flight["arrival"]

        block = (
            f"વિકલ્પ {index}:\n"
            f"{airline} ફ્લાઇટ. {stops}.\n"
            f"પ્રસ્થાન {departure} વાગ્યે, આગમન {arrival} વાગ્યે.\n"
            f"સમયગાળો {duration} મિનિટ.\n"
            f"ભાડું રૂ. {price}."
        )

        lines.append(block)

    return "\n\n".join(lines)


def generate_flight_response_english(flights):
    """
    English version used for printing to the terminal so the
    developer can read what the agent said.
    """

    if not flights:
        return "Sorry, I could not find any flights."

    top_flights = flights[:3]

    lines = [f"I found {len(top_flights)} flight options.\n"]

    for index, flight in enumerate(top_flights, start=1):

        stops    = _stops_label_english(flight.get("stops", 0))
        price    = int(flight["price"])
        duration = flight["duration_minutes"]

        block = (
            f"Option {index}:\n"
            f"{flight['airline']} flight. {stops}.\n"
            f"Departure at {flight['departure']}. Arrival at {flight['arrival']}.\n"
            f"Duration is {duration} minutes.\n"
            f"Ticket price is Rs. {price}."
        )

        lines.append(block)

    return "\n\n".join(lines)