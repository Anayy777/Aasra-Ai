"""
Converts the guided-conversation profile dict (from
conversation_state.py's session["profile"]) into the recommendation
service's BeneficiaryProfile schema
"""

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recommendation-service"))

from app.models import BeneficiaryProfile, Mobility  # noqa: E402
from app.nlu import client  # noqa: E402  (reuse the configured Groq client)
from app.normalizer import normalize_skill  # noqa: E402


def _extract_skills_list(skills_text: str) -> list:
    """LLM-based extraction with a naive-split fallback if the API call fails."""
    if not skills_text or not skills_text.strip():
        return []

    try:
        prompt = f"""Extract a short list of individual skills or interests
from this text. Return ONLY a JSON array of strings, nothing else.

Text: "{skills_text}"
"""
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=100,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        skills = json.loads(raw)
        if isinstance(skills, list) and skills:
            return [normalize_skill(s) for s in skills if s]
    except Exception as e:
        print(f"Skill extraction via LLM failed ({e}), falling back to naive split.")

    parts = re.split(r",| and | aur |/", skills_text, flags=re.IGNORECASE)
    return [normalize_skill(p.strip()) for p in parts if p.strip()]


def _extract_max_distance_km(mobility_text: str):
    if not mobility_text:
        return 25.0
    match = re.search(r"(\d+)\s*(km|kilometer|kilometre)", mobility_text.lower())
    if match:
        return float(match.group(1))
    if any(p in mobility_text.lower() for p in ["no constraint", "can travel", "anywhere", "koi dikkat nahi"]):
        return 50.0
    return 25.0


def _extract_employment_preference(text: str):
    """
    NOTE: currently unused by the matching engine (nqr_matcher.py /
    nqr_ranker.py don't reference employment_preference), but populated
    for when that gets wired in. Uses self_employment/wage_employment
    to match the PS's actual wording -- flag to the team if this needs
    to align with recommendation-service/app/normalizer.py's current
    full_time/part_time mapping.
    """
    if not text:
        return None
    text_lower = text.lower()
    wage_phrases = ["someone else", "for someone", "work for", "employed by", "a job", "naukri", "salary", "wage"]
    self_employment_phrases = ["own business", "own work", "my own", "self employ", "start my", "khud ka", "apna"]
    if any(p in text_lower for p in wage_phrases):
        return "wage_employment"
    if any(p in text_lower for p in self_employment_phrases):
        return "self_employment"
    return None


def build_beneficiary_profile(raw_profile: dict) -> BeneficiaryProfile:
    """
    raw_profile (from conversation_state.py) looks like:
        {
            "name": "...", "location": "...", "education": "...",
            "family_occupation": "...", "current_livelihood": "...",
            "skills_interest": "...", "mobility": "...",
            "employment_preference": "...",
        }
    """
    occupation_text = raw_profile.get("current_livelihood") or raw_profile.get("family_occupation")

    return BeneficiaryProfile(
        education=raw_profile.get("education"),  # normalize_profile() will clean this
        occupation=occupation_text,
        skills=_extract_skills_list(raw_profile.get("skills_interest", "")),
        location=(raw_profile.get("location") or "").strip() or None,
        mobility=Mobility(max_distance_km=_extract_max_distance_km(raw_profile.get("mobility", ""))),
        employment_preference=_extract_employment_preference(raw_profile.get("employment_preference", "")),
        language_code=raw_profile.get("language_code"),
        special_categories=[],  # not currently collected by our guided flow
    )