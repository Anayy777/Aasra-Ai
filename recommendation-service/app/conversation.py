from app.models import BeneficiaryProfile
from app.nlu import extract_profile, update_profile_from_answer
from app.normalizer import normalize_profile
from app.profile_completeness import (
    get_missing_fields,
    get_next_question,
    is_profile_complete
)
from app.recommender import recommend_from_profile


def start_conversation(
    transcript: str,
    language_code: str = "hi-IN",
    user_latitude: float = None,
    user_longitude: float = None,
    top_k: int = 3
):
    """
    Start a beneficiary conversation from the first transcript.

    If the profile is complete, generate recommendations.
    Otherwise, return the next question.
    """

    # Step 1: Extract profile
    profile = extract_profile(
        transcript,
        language_code=language_code
    )

    # Step 2: Normalize profile
    profile = normalize_profile(profile)

    # Step 3: Check missing information
    missing_fields = get_missing_fields(profile)

    # Step 4: If profile is complete, recommend courses
    if is_profile_complete(profile):

        recommendation_result = recommend_from_profile(
            profile=profile,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            top_k=top_k,
            language_code=language_code
        )

        return {
            "profile": profile,
            "missing_fields": [],
            "next_question": None,
            "complete": True,
            "recommendations": recommendation_result["recommendations"],
            "reply": recommendation_result["reply"]
        }

    # Step 5: Otherwise ask for missing information
    next_question = get_next_question(
        missing_fields,
        language_code
    )

    return {
        "profile": profile,
        "missing_fields": missing_fields,
        "next_question": next_question,
        "complete": False,
        "recommendations": [],
        "reply": next_question
    }


def continue_conversation(
    profile: BeneficiaryProfile,
    answer: str,
    language_code: str = "hi-IN",
    user_latitude: float = None,
    user_longitude: float = None,
    top_k: int = 3
):
    """
    Update an existing profile using the beneficiary's
    latest answer.

    If the profile becomes complete, generate recommendations.
    Otherwise, ask the next question.
    """

    # Step 1: Update existing profile
    updated_profile = update_profile_from_answer(
        profile,
        answer
    )

    # Step 2: Normalize updated profile
    updated_profile = normalize_profile(updated_profile)

    # Step 3: Check missing information
    missing_fields = get_missing_fields(updated_profile)

    # Step 4: If profile is complete, recommend courses
    if is_profile_complete(updated_profile):

        recommendation_result = recommend_from_profile(
            profile=updated_profile,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
            top_k=top_k,
            language_code=language_code
        )

        return {
            "profile": updated_profile,
            "missing_fields": [],
            "next_question": None,
            "complete": True,
            "recommendations": recommendation_result["recommendations"],
            "reply": recommendation_result["reply"]
        }

    # Step 5: Otherwise ask for next missing information
    next_question = get_next_question(
        missing_fields,
        language_code
    )

    return {
        "profile": updated_profile,
        "missing_fields": missing_fields,
        "next_question": next_question,
        "complete": False,
        "recommendations": [],
        "reply": next_question
    }