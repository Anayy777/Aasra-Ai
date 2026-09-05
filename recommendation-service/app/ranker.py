from app.matcher import is_eligible
from app.skill_matcher import calculate_skill_similarity
from app.location import haversine_distance


def calculate_location_score(distance, max_distance):
    """
    Convert distance into a score between 0 and 1.

    Closer course = higher score.
    """

    if max_distance is None:
        return 0.0

    if distance >= max_distance:
        return 0.0

    score = 1 - (distance / max_distance)

    return score


def rank_courses(
    profile,
    courses,
    user_latitude=None,
    user_longitude=None
):
    """
    Filter eligible courses and rank them
    using skill relevance and location.
    """

    ranked_courses = []

    for course in courses:

        # Step 1: Eligibility
        if not is_eligible(
            profile,
            course,
            user_latitude,
            user_longitude
        ):
            continue

        # Step 2: Skill similarity
        skill_score = calculate_skill_similarity(
            profile.skills,
            course["skills"]
        )

        # Step 3: Calculate distance
        distance = None
        location_score = 0.0

        if (
            user_latitude is not None
            and user_longitude is not None
            and course.get("latitude") is not None
            and course.get("longitude") is not None
        ):
            distance = haversine_distance(
                user_latitude,
                user_longitude,
                course["latitude"],
                course["longitude"]
            )

            location_score = calculate_location_score(
                distance,
                profile.mobility.max_distance_km
            )

        # Step 4: Final score
        final_score = (
            0.7 * skill_score
            + 0.3 * location_score
        )

        ranked_courses.append({
            "course_id": course["course_id"],
            "course_name": course["name"],
            "skill_score": skill_score,
            "location_score": location_score,
            "distance_km": distance,
            "final_score": final_score
        })

    # Step 5: Highest score first
    ranked_courses.sort(
        key=lambda course: course["final_score"],
        reverse=True
    )

    return ranked_courses

