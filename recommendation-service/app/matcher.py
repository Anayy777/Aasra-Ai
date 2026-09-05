from app.location import haversine_distance


def is_eligible(
    profile,
    course,
    user_latitude=None,
    user_longitude=None
):
    """
    Check whether a beneficiary is eligible for a course.
    """

    # Education requirement
    required_education = course.get("education_requirement")

    if required_education:
        if not education_is_sufficient(
            profile.education,
            required_education
        ):
            return False

    # Employment preference
    employment_preference = profile.employment_preference

    if employment_preference:
        available_types = course.get("employment_type", [])

        if employment_preference not in available_types:
            return False

    # Distance requirement
    max_distance = profile.mobility.max_distance_km

    if (
        max_distance is not None
        and user_latitude is not None
        and user_longitude is not None
    ):
        course_latitude = course.get("latitude")
        course_longitude = course.get("longitude")

        if (
            course_latitude is not None
            and course_longitude is not None
        ):
            distance = haversine_distance(
                user_latitude,
                user_longitude,
                course_latitude,
                course_longitude
            )

            if distance > max_distance:
                return False

    return True


def education_is_sufficient(
    user_education,
    required_education
):
    """
    Compare beneficiary education with course requirement.
    """

    if not user_education:
        return True

    education_levels = {
        "5th": 1,
        "8th": 2,
        "10th": 3,
        "12th": 4,
        "graduate": 5,
        "postgraduate": 6
    }

    user_level = education_levels.get(
        user_education.lower()
    )

    required_level = education_levels.get(
        required_education.lower()
    )

    if user_level is None or required_level is None:
        return True

    return user_level >= required_level