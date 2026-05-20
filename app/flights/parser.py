from datetime import datetime

def format_time(iso_string):

    dt = datetime.fromisoformat(iso_string)

    return dt.strftime("%I:%M %p")
def parse_flights(raw_response):

        itineraries = raw_response.get("itineraries", [])

        parsed_flights = []

        for itinerary in itineraries:

            leg = itinerary["legs"][0]

            carrier = leg["carriers"][0]

            parsed_flights.append({

                "airline": carrier.get("name"),

                "price": itinerary["price"].get("amount"),

                "currency": itinerary["price"].get("currency"),
                
                "departure": format_time(leg.get("departure")),
                
                "arrival": format_time(leg.get("arrival")),

                "duration_minutes": leg.get("durationMinutes"),

                "stops": leg.get("stopCount"),

                "booking_url": itinerary.get("bookingUrl")
            })

        return parsed_flights