def rank_flights(flights):

    ranked = []

    for flight in flights:

        score = 0

        # Lower price = better
        score += float(flight["price"]) * 0.6

        # Duration penalty
        score += flight["duration_minutes"] * 0.3

        # Stop penalty
        score += flight["stops"] * 500

        flight["score"] = score

        ranked.append(flight)

    ranked.sort(key=lambda x: x["score"])

    return ranked