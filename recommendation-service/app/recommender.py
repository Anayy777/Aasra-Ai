from app.nlu import extract_profile
from app.normalizer import normalize_profile
from app.nqr_loader import load_nqr_qualifications
from app.nqr_ranker import rank_qualifications
from app.response_formatter import format_recommendation_reply


def recommend_from_profile(
    profile,
    user_latitude=None,
    user_longitude=None,
    top_k=3,
    language_code=None,
):
    """
    Generate qualification recommendations from an
    already extracted and normalized beneficiary profile.

    The recommendation pipeline is:

        Profile
          ↓
        NQR Loader
          ↓
        NQR Ranker
          ↓
        Top K Qualifications
          ↓
        Human-readable Reply
    """

    if top_k < 1:
        top_k = 1

    # Step 1: Load active NQR qualifications.
    qualifications = load_nqr_qualifications()

    # Step 2: Rank qualifications against the profile.
    ranked_qualifications = rank_qualifications(
        profile=profile,
        qualifications=qualifications,
        top_k=top_k,
    )

    # Step 3: Convert ranked Qualification objects
    # into API-friendly dictionaries.
    recommendations = []

    for item in ranked_qualifications:

        qualification = item["qualification"]

        recommendation = {
            "qualification_id": (
                qualification.qualification_id
            ),
            "qualification_title": (
                qualification.title
            ),
            "description": (
                qualification.description
            ),
            "sector": qualification.sector,
            "nsqf_level": qualification.nsqf_level,
            "qualification_type": (
                qualification.qualification_type
            ),
            "proposed_occupations": (
                qualification.proposed_occupation
            ),
            "progression_pathway": (
                qualification.progression_pathway
            ),
            "specializations": (
                qualification.specializations
            ),
            "is_instructor_or_trainer": (
                qualification.is_instructor_or_trainer
            ),
            "relevance_score": (
                item["relevance_score"]
            ),
            "specificity_score": (
                item["specificity_score"]
            ),
            "final_score": (
                item["final_score"]
            ),
        }

        recommendations.append(
            recommendation
        )

    result = {
        "profile": profile.model_dump(),
        "recommendations": recommendations,
    }

    # Step 4: Generate human-readable response.
    result["reply"] = format_recommendation_reply(
        result,
        language_code=language_code,
    )

    return result


def recommend_from_transcript(
    transcript,
    user_latitude=None,
    user_longitude=None,
    top_k=3,
    language_code=None,
):
    """
    Convert a beneficiary transcript into a normalized
    profile and generate ranked NQR recommendations.
    """

    # Step 0: Validate transcript.
    if not transcript or not transcript.strip():
        return {
            "profile": None,
            "recommendations": [],
            "reply": (
                "Mujhe aapki information samajh nahi aayi. "
                "Please dobara batayein."
            ),
        }

    # Step 1: Extract structured profile using Qwen.
    profile = extract_profile(
        transcript,
        language_code=language_code,
    )

    # Step 2: Normalize extracted profile.
    profile = normalize_profile(
        profile
    )

    # Step 3: Reuse profile-based NQR recommendation pipeline.
    return recommend_from_profile(
        profile=profile,
        user_latitude=user_latitude,
        user_longitude=user_longitude,
        top_k=top_k,
        language_code=language_code,
    )