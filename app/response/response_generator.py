def generate_flight_response(flights):

    if not flights:
        return "Sorry, I could not find any flights."

    response = []

    response.append(
        f"I found {len(flights)} flight options."
    )

    top_flights = flights[:3]

    for index, flight in enumerate(top_flights, start=1):

        text = f"""
Option {index}:

{flight['airline']} flight.

Departure at {flight['departure']}.

Arrival at {flight['arrival']}.

Duration is {flight['duration_minutes']} minutes.

Ticket price is rupees {int(flight['price'])}.
"""

        response.append(text.strip())

    return "\n\n".join(response)