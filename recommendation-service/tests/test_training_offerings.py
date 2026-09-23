from datetime import date, timedelta

from app.models import BeneficiaryProfile, Mobility
from app.training_offerings import load_training_offerings, match_training_offerings
from app.nqr_loader import load_nqr_qualifications
from app.recommender import recommend_from_profile
from app.response_formatter import format_recommendation_reply


def test_offering_respects_distance_preference_access_and_freshness():
    profile = BeneficiaryProfile(
        location="Indore",
        mobility=Mobility(max_distance_km=20, physical_constraints="uses a wheelchair"),
        employment_preference="wage_employment",
    )
    base = {
        "qualification_id": "Q1", "centre_name": "Example Centre",
        "provider_name": "Example Provider", "source_url": "https://example.org/batch",
        "district": "Indore", "state": "Madhya Pradesh", "latitude": "22.72",
        "longitude": "75.86", "status": "open", "start_date": "",
        "verified_at": date.today().isoformat(),
        "accessibility_confirmed": "yes", "employment_pathway": "wage_employment",
    }
    far = {**base, "batch_id": "far", "latitude": "23.30"}
    inaccessible = {**base, "batch_id": "inaccessible", "accessibility_confirmed": "no"}
    stale = {**base, "batch_id": "stale", "verified_at": (date.today() - timedelta(days=31)).isoformat()}
    self_employment = {**base, "batch_id": "self", "employment_pathway": "self_employment"}
    suitable = {**base, "batch_id": "suitable"}

    matches = match_training_offerings(
        profile, "Q1", [far, inaccessible, stale, self_employment, suitable],
        latitude=22.72, longitude=75.86,
    )
    assert [item["batch_id"] for item in matches] == ["suitable", "self"]
    assert matches[0]["accessibility"] == "confirmed"
    assert matches[0]["preference_match"] is True


def test_locality_required_without_coordinates():
    profile = BeneficiaryProfile(location="Indore")
    offering = {
        "qualification_id": "Q1", "district": "Bhopal", "status": "open",
        "batch_id": "B1", "centre_name": "Example Centre",
        "provider_name": "Example Provider", "source_url": "https://example.org/batch",
        "verified_at": date.today().isoformat(),
    }
    assert match_training_offerings(profile, "Q1", [offering]) == []


def test_recommender_attaches_verified_batch(monkeypatch):
    qualification = load_nqr_qualifications()[0]
    monkeypatch.setattr(
        "app.recommender.load_training_offerings",
        lambda: [{
            "qualification_id": qualification.qualification_id,
            "batch_id": "B1", "centre_name": "Example Centre",
            "provider_name": "Example Provider", "district": "Indore",
            "state": "Madhya Pradesh", "status": "open",
            "source_url": "https://example.org/batch",
            "verified_at": date.today().isoformat(),
            "employment_pathway": "both",
        }],
    )
    monkeypatch.setattr(
        "app.recommender.rank_qualifications",
        lambda **kwargs: [{
            "qualification": qualification, "relevance_score": 0.8,
            "specificity_score": 0.7, "final_score": 0.775,
        }],
    )
    result = recommend_from_profile(BeneficiaryProfile(location="Indore"), top_k=1)
    assert result["training_availability"] == "verified_options_available"
    assert result["recommendations"][0]["training_options"][0]["batch_id"] == "B1"
    assert "Batch ID: B1" in result["reply"]
    assert "Register if you are new, or log in" in result["reply"]
    assert "Complete e-KYC if it is pending" in result["reply"]


def test_empty_catalogue_does_not_imply_an_available_batch():
    assert load_training_offerings() == []
    reply = format_recommendation_reply({
        "recommendations": [{
            "qualification_title": "Example qualification", "training_options": [],
        }],
    })
    assert "No verified local training batch is listed yet" in reply
    assert "https://www.skillindiadigital.gov.in/home" in reply
