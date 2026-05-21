from datetime import datetime


def format_time(iso_string):

    if not iso_string:
        return "N/A"

    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%I:%M %p")
    except (ValueError, TypeError):
        return "N/A"


def parse_flights(raw_response):

    if not raw_response or not isinstance(raw_response, dict):
        return []

    itineraries = raw_response.get("itineraries", [])

    if not itineraries:
        return []

    parsed_flights = []

    for itinerary in itineraries:

        try:
            legs = itinerary.get("legs", [])
            if not legs:
                continue

            leg = legs[0]

            carriers = leg.get("carriers", [])
            if not carriers:
                continue

            carrier = carriers[0]

            price_data = itinerary.get("price", {})
            price = price_data.get("amount")
            duration = leg.get("durationMinutes")
            stops = leg.get("stopCount")

            # Skip flights with missing critical fields
            if price is None or duration is None or stops is None:
                continue

            parsed_flights.append({
                "airline": carrier.get("name", "Unknown Airline"),
                "price": price,
                "currency": price_data.get("currency", "INR"),
                "departure": format_time(leg.get("departure")),
                "arrival": format_time(leg.get("arrival")),
                "duration_minutes": duration,
                "stops": stops,
                "booking_url": itinerary.get("bookingUrl")
            })

        except Exception:
            # Skip any malformed itinerary and continue with the rest
            continue

    return parsed_flights
