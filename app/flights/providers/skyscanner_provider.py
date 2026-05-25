import os
import requests

from dotenv import load_dotenv

load_dotenv()


class SkyScannerProvider:

    def __init__(self):

        self.api_key = os.getenv("RAPIDAPI_KEY")
        self.host = os.getenv("RAPIDAPI_HOST")

        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.host
        }

    def search_airport(self, city_name):

        url = "https://skyscanner-flights-travel-api.p.rapidapi.com/flights/searchAirport"

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params={"query": city_name},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            raise RuntimeError("Airport search timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("No internet connection. Please check your network.")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Airport search failed with status {response.status_code}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during airport search: {e}")

        airports = data.get("places", [])

        if not airports:
            return None

        first = airports[0]

        return {
            "skyId": first.get("skyId"),
            "entityId": first.get("entityId"),
            "name": first.get("name"),
            "city": first.get("cityName"),
            "country": first.get("countryName")
        }

    def search_flights(
        self,
        source_airport,
        destination_airport,
        date,
        passengers=1,
        travel_class="economy"
    ):
        """
        passengers   — number of adult passengers (default 1)
        travel_class — "economy", "business", or "first" (default "economy")
        """

        # Normalise travel_class to what the API accepts
        valid_classes = {"economy", "business", "first"}
        cabin = travel_class.lower() if travel_class and travel_class.lower() in valid_classes else "economy"

        url = "https://skyscanner-flights-travel-api.p.rapidapi.com/flights/searchFlights"

        querystring = {
            "originSkyId": source_airport["skyId"],
            "destinationSkyId": destination_airport["skyId"],
            "originEntityId": source_airport["entityId"],
            "destinationEntityId": destination_airport["entityId"],
            "date": date,
            "cabinClass": cabin,
            "adults": str(passengers),
            "currency": "INR",
            "market": "IN",
            "countryCode": "IN"
        }

        try:
            response = requests.get(
                url,
                headers=self.headers,
                params=querystring,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.Timeout:
            raise RuntimeError("Flight search timed out. Please try again.")
        except requests.exceptions.ConnectionError:
            raise RuntimeError("No internet connection. Please check your network.")
        except requests.exceptions.HTTPError as e:
            raise RuntimeError(f"Flight search failed with status {response.status_code}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during flight search: {e}")

        return data