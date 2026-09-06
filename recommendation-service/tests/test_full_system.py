from fastapi.testclient import TestClient

from app.api import app
from app.conversation import (
    start_conversation,
    continue_conversation,
)
from app.eligibility import check_qualification_eligibility
from app.models import BeneficiaryProfile, Qualification
from app.nqr_loader import load_nqr_qualifications
from app.nqr_matcher import match_qualification
from app.nqr_normalizer import (
    normalize_text,
    get_normalized_qualification_text,
)
from app.nqr_ranker import rank_qualifications
from app.normalizer import normalize_profile
from app.profile_completeness import (
    get_missing_fields,
    is_profile_complete,
)
from app.recommender import recommend_from_profile
from app.response_formatter import format_recommendation_reply
from app.special_category import detect_special_categories
from app.trade_classifier import classify_trade


client = TestClient(app)


def build_electrician_profile():
    return BeneficiaryProfile(
        education="12th",
        occupation="Electrician",
        skills=[
            "electrical wiring",
            "maintenance",
        ],
        location="Delhi",
        employment_preference="full_time",
        language_code="hi-IN",
    )


def test_complete_recommendation_pipeline():
    """
    Main end-to-end test for the recommendation engine.

    Flow:
        Profile
        -> Normalization
        -> NQR loading
        -> Eligibility
        -> Matching
        -> Ranking
        -> Recommendation
        -> Response
    """

    profile = build_electrician_profile()

    # 1. Normalize profile
    profile = normalize_profile(profile)

    assert profile.education == "12th"
    assert profile.occupation == "electrician"
    assert "electrical wiring" in profile.skills
    assert profile.location == "Delhi"
    assert profile.employment_preference == "full_time"

    # 2. Profile completeness
    assert is_profile_complete(profile)
    assert get_missing_fields(profile) == []

    # 3. Load real NQR dataset
    qualifications = load_nqr_qualifications()

    assert len(qualifications) > 0

    # 4. Check real qualification structure
    qualification = qualifications[0]

    assert qualification.qualification_id
    assert qualification.title

    # 5. Normalize qualification text
    normalized = get_normalized_qualification_text(
        qualification
    )

    assert normalized["title"]
    assert isinstance(
        normalized["proposed_occupations"],
        list,
    )

    # 6. Trade classification
    trade_info = classify_trade(profile)

    assert trade_info["trade_family"] == "electrician"

    # 7. Match profile against a qualification
    match = match_qualification(
        profile,
        qualification,
    )

    assert match is not None
    assert "relevance_score" in match
    assert 0.0 <= match["relevance_score"] <= 1.0

    # 8. Eligibility
    eligibility = check_qualification_eligibility(
        profile,
        qualification,
    )

    assert isinstance(eligibility, dict)
    assert "eligible" in eligibility

    # 9. Rank real NQR qualifications
    ranked = rank_qualifications(
        profile,
        qualifications,
        top_k=3,
    )

    assert len(ranked) > 0
    assert len(ranked) <= 3

    for item in ranked:
        assert "qualification" in item
        assert "relevance_score" in item
        assert "specificity_score" in item
        assert "final_score" in item

        assert 0.0 <= item["final_score"] <= 1.0

    # Ranking should be descending.
    scores = [
        item["final_score"]
        for item in ranked
    ]

    assert scores == sorted(
        scores,
        reverse=True,
    )

    # 10. Full recommendation response
    result = recommend_from_profile(
        profile=profile,
        top_k=3,
        language_code="hi-IN",
    )

    assert "profile" in result
    assert "recommendations" in result
    assert "reply" in result

    assert len(result["recommendations"]) > 0
    assert result["reply"]


def test_profile_normalization():
    profile = BeneficiaryProfile(
        education="12th pass",
        occupation=" Electrician ",
        skills=[
            "wiring",
            "maintenance",
        ],
        location=" Delhi ",
        employment_preference="Full-Time",
    )

    normalized = normalize_profile(profile)

    assert normalized.education == "12th"
    assert normalized.occupation == "electrician"
    assert normalized.skills[0] == "electrical wiring"
    assert normalized.location == "Delhi"
    assert normalized.employment_preference == "full_time"


def test_incomplete_profile_flow():
    profile = BeneficiaryProfile(
        occupation="electrician",
    )

    assert not is_profile_complete(profile)

    missing_fields = get_missing_fields(profile)

    assert "location" in missing_fields
    assert "education" in missing_fields
    assert "skills" in missing_fields
    assert "employment_preference" in missing_fields


def test_conversation_flow():
    """
    Verify that conversation logic asks for missing
    information and eventually reaches recommendation.
    """

    first = start_conversation(
        transcript="Main electrician hoon.",
        language_code="hi-IN",
        top_k=3,
    )

    assert first["profile"] is not None
    assert first["complete"] is False
    assert first["next_question"]

    profile = first["profile"]

    second = continue_conversation(
        profile=profile,
        answer="Main Delhi mein rehta hoon.",
        language_code="hi-IN",
        top_k=3,
    )

    assert second["profile"].location == "Delhi"

    profile = second["profile"]

    third = continue_conversation(
        profile=profile,
        answer="Main 12th pass hoon.",
        language_code="hi-IN",
        top_k=3,
    )

    assert third["profile"].education == "12th"

    profile = third["profile"]

    fourth = continue_conversation(
        profile=profile,
        answer="Mujhe wiring aur maintenance ka kaam aata hai.",
        language_code="hi-IN",
        top_k=3,
    )

    assert "electrical wiring" in fourth["profile"].skills
    assert "maintenance" in fourth["profile"].skills

    profile = fourth["profile"]

    fifth = continue_conversation(
        profile=profile,
        answer="Main full-time kaam prefer karta hoon.",
        language_code="hi-IN",
        top_k=3,
    )

    assert fifth["profile"].employment_preference == "full_time"
    assert fifth["complete"] is True
    assert fifth["recommendations"]


def test_special_category_protection():
    normal_profile = build_electrician_profile()

    divyangjan_qualification = Qualification(
        qualification_id="TEST-DIVYANGJAN",
        title="Assistant Electrician-(Divyangjan) LD",
        description="Electrical qualification for Divyangjan",
        sector="Construction",
        nsqf_level=3,
    )

    categories = detect_special_categories(
        divyangjan_qualification
    )

    assert "divyangjan" in categories

    eligibility = check_qualification_eligibility(
        normal_profile,
        divyangjan_qualification,
    )

    assert eligibility["eligible"] is False

    special_profile = build_electrician_profile()
    special_profile.special_categories = [
        "divyangjan"
    ]

    eligibility = check_qualification_eligibility(
        special_profile,
        divyangjan_qualification,
    )

    assert eligibility["eligible"] is True


def test_response_formatter():
    result = {
        "recommendations": [
            {
                "qualification_title": "Electrician",
                "final_score": 0.85,
                "nsqf_level": 4.0,
                "sector": "Electrical",
                "proposed_occupations": [
                    "Electrician"
                ],
                "progression_pathway": None,
            }
        ]
    }

    reply = format_recommendation_reply(
        result,
        language_code="hi-IN",
    )

    assert reply
    assert "Electrician" in reply
    assert "85%" in reply


def test_api_health():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "running"


def test_api_recommendation_endpoint():
    payload = {
        "transcript": (
            "Main electrician hoon, "
            "Delhi mein rehta hoon, "
            "12th pass hoon, "
            "mujhe wiring aur maintenance aata hai, "
            "full-time kaam chahiye"
        ),
        "language_code": "hi-IN",
        "top_k": 3,
    }

    response = client.post(
        "/recommend",
        json=payload,
    )

    assert response.status_code == 200

    data = response.json()

    assert "profile" in data
    assert "recommendations" in data
    assert "reply" in data

    assert data["profile"]["occupation"] == "electrician"
    assert data["profile"]["education"] == "12th"
    assert data["profile"]["location"] == "Delhi"
    assert data["profile"]["employment_preference"] == "full_time"

    assert len(data["recommendations"]) > 0
    assert data["reply"]