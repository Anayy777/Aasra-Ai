import json

from app.nlu import extract_profile
from app.normalizer import normalize_profile
from app.ranker import rank_courses
from app.response_formatter import format_recommendation_reply


def recommend_from_transcript(
    transcript,
    user_latitude,
    user_longitude,
    top_k=3
):
    """
    Convert a beneficiary transcript into ranked
    course recommendations.
    """

    # Step 0: Validate transcript
    if not transcript or not transcript.strip():
        return {
            "profile": None,
            "recommendations": [],
            "reply": "Mujhe aapki information samajh nahi aayi. Please dobara batayein."
        }

    # Step 1: Extract structured profile using Qwen
    profile = extract_profile(transcript)

    # Step 2: Normalize extracted profile
    profile = normalize_profile(profile)

    # Step 3: Load course data
    with open(
        "data/courses.json",
        "r",
        encoding="utf-8"
    ) as file:
        courses = json.load(file)

    # Step 4: Rank courses
    ranked_courses = rank_courses(
        profile,
        courses,
        user_latitude,
        user_longitude
    )

    # Step 5: Return top recommendations
    recommendations = ranked_courses[:top_k]

    result = {
        "profile": profile.model_dump(),
        "recommendations": recommendations
    }

    result["reply"] = format_recommendation_reply(result)

    return result