REQUIRED_FIELDS = [
    "location",
    "education",
    "skills",
    "employment_preference"
]


def get_missing_fields(profile):
    """
    Return important profile fields that are still missing.
    """

    missing_fields = []

    if not profile.location:
        missing_fields.append("location")

    if not profile.education:
        missing_fields.append("education")

    if not profile.skills:
        missing_fields.append("skills")

    if not profile.employment_preference:
        missing_fields.append("employment_preference")

    return missing_fields


def is_profile_complete(profile):
    """
    Check whether all required profile fields are available.
    """

    return len(get_missing_fields(profile)) == 0
def get_next_question(missing_fields, language_code="hi-IN"):
    """
    Return the next question based on the missing field
    and detected language.
    """

    if not missing_fields:
        return None

    language = language_code.lower().split("-")[0]

    questions = {
        "hi": {
            "location": "Aap kis city ya gaon mein rehte hain?",
            "education": "Aapki highest education kya hai?",
            "skills": "Aapko kaun-kaun se kaam ya skills aate hain?",
            "employment_preference": (
                "Aap full-time ya part-time kaam prefer karenge?"
            )
        },

        "en": {
            "location": "Which city or village do you live in?",
            "education": "What is your highest level of education?",
            "skills": "What skills or types of work do you know?",
            "employment_preference": (
                "Do you prefer full-time or part-time work?"
            )
        }
    }

    next_field = missing_fields[0]

    language_questions = questions.get(
        language,
        questions["en"]
    )

    return language_questions[next_field]