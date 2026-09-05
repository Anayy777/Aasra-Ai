def format_recommendation_reply(result):
    """
    Convert recommendation results into a
    human-readable response.
    """

    recommendations = result.get("recommendations", [])

    if not recommendations:
        return (
            "Aapke profile ke liye abhi koi suitable "
            "course nahi mila."
        )

    lines = [
        "Aapke profile ke hisaab se ye courses suitable hain:\n"
    ]

    for index, course in enumerate(recommendations, start=1):

        course_name = course["course_name"]

        final_score = course["final_score"]
        match_percentage = round(final_score * 100)

        distance = course.get("distance_km")

        if distance is not None:
            distance_text = f"{distance:.1f} km"
        else:
            distance_text = "distance unavailable"

        lines.append(
            f"{index}. {course_name}\n"
            f"   Match: {match_percentage}%\n"
            f"   Distance: {distance_text}\n"
        )

    return "\n".join(lines)