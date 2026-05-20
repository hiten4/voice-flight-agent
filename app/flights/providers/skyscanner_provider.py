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

        querystring = {
            "query": city_name
        }

        response = requests.get(
            url,
            headers=self.headers,
            params=querystring
        )

        data = response.json()

        # print("\nRAW API RESPONSE:")
        # print(data)

        airports = data.get("places", [])

        if not airports:
            return None

        first_result = airports[0]

        return {
            "skyId": first_result.get("skyId"),
            "entityId": first_result.get("entityId"),
            "name": first_result.get("name"),
            "city": first_result.get("cityName"),
            "country": first_result.get("countryName")
        }
    def search_flights(
    self,
    source_airport,
    destination_airport,
    date
    ):

        origin_entity_id = source_airport["entityId"]
        destination_entity_id = destination_airport["entityId"]

        url = "https://skyscanner-flights-travel-api.p.rapidapi.com/flights/searchFlights"

        querystring = {
        "originSkyId": source_airport["skyId"],
        "destinationSkyId": destination_airport["skyId"],
        "originEntityId": source_airport["entityId"],
        "destinationEntityId": destination_airport["entityId"],
        "date": date,
        "cabinClass": "economy",
        "adults": "1",
        "currency": "INR",
        "market": "IN",
        "countryCode": "IN"
        }

        # print("\nREQUEST URL:", url)
        # print("QUERY PARAMS:", querystring)

        response = requests.get(
            url,
            headers=self.headers,
            params=querystring
        )

        data = response.json()

        # print("\nRAW FLIGHT RESPONSE:")
        # print(data)

        return data
    