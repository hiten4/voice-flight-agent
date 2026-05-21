def rank_flights(flights):

    if not flights:
        return []

    ranked = []

    for flight in flights:

        try:
            score = 0

            # Lower price = better
            score += float(flight["price"]) * 0.6

            # Duration penalty
            score += float(flight["duration_minutes"]) * 0.3

            # Stop penalty
            score += int(flight["stops"]) * 500

            flight["score"] = score

            ranked.append(flight)

        except (TypeError, ValueError, KeyError):
            # Skip any flight with unscoreable data
            continue

    ranked.sort(key=lambda x: x["score"])

    return ranked
