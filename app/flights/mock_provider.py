"""
Mock provider for development and testing.
Returns fake flight data instantly — no API calls, no rate limits.

Usage in main.py:
    Set USE_MOCK=True at the top to use this instead of SkyScannerProvider.
"""

MOCK_AIRPORTS = {
    "delhi":     {"skyId": "DEL", "entityId": "128668647", "name": "Delhi", "city": "Delhi", "country": "India"},
    "mumbai":    {"skyId": "BOM", "entityId": "95673320",  "name": "Mumbai", "city": "Mumbai", "country": "India"},
    "ahmedabad": {"skyId": "AMD", "entityId": "128668632", "name": "Ahmedabad", "city": "Ahmedabad", "country": "India"},
    "bangalore": {"skyId": "BLR", "entityId": "95673336",  "name": "Bangalore", "city": "Bangalore", "country": "India"},
    "chennai":   {"skyId": "MAA", "entityId": "128668648", "name": "Chennai", "city": "Chennai", "country": "India"},
    "kolkata":   {"skyId": "CCU", "entityId": "128668649", "name": "Kolkata", "city": "Kolkata", "country": "India"},
}

MOCK_FLIGHTS = {
    "itineraries": [
        {
            "price": {"amount": 4500, "currency": "INR"},
            "legs": [{"carriers": [{"name": "IndiGo"}], "departure": "2026-06-01T06:00:00", "arrival": "2026-06-01T08:10:00", "durationMinutes": 130, "stopCount": 0}],
            "bookingUrl": "https://example.com/book/1"
        },
        {
            "price": {"amount": 5200, "currency": "INR"},
            "legs": [{"carriers": [{"name": "Air India"}], "departure": "2026-06-01T09:30:00", "arrival": "2026-06-01T11:45:00", "durationMinutes": 135, "stopCount": 0}],
            "bookingUrl": "https://example.com/book/2"
        },
        {
            "price": {"amount": 3800, "currency": "INR"},
            "legs": [{"carriers": [{"name": "SpiceJet"}], "departure": "2026-06-01T14:00:00", "arrival": "2026-06-01T17:00:00", "durationMinutes": 180, "stopCount": 1}],
            "bookingUrl": "https://example.com/book/3"
        },
    ]
}


class MockFlightProvider:

    def search_airport(self, city_name):
        result = MOCK_AIRPORTS.get(city_name.lower().strip())
        if not result:
            # Return a generic airport for any unknown city
            return {
                "skyId": city_name[:3].upper(),
                "entityId": "000000",
                "name": city_name,
                "city": city_name,
                "country": "India"
            }
        return result

    def search_flights(self, source_airport, destination_airport, date, passengers=1, travel_class="economy"):
        print(f"[MOCK] Searching {source_airport['city']} → {destination_airport['city']} on {date} ({passengers} pax, {travel_class})")
        return MOCK_FLIGHTS