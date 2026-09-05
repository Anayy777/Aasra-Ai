from app.models import BeneficiaryProfile
from app.normalizer import normalize_profile


profile = BeneficiaryProfile(
    education="12th pass",
    occupation="Electrician",
    skills=["Electrical Wiring", "Maintenance"],
    location="Delhi",
    employment_preference="full time"
)

normalized_profile = normalize_profile(profile)

print(normalized_profile.model_dump())

print("\nSKILL ALIAS TEST")

from app.models import BeneficiaryProfile
from app.normalizer import normalize_profile

alias_profile = BeneficiaryProfile(
    education="12th",
    occupation="electrician",
    skills=["wiring", "bijli ka kaam"],
    location="Delhi",
    employment_preference="full time"
)

alias_profile = normalize_profile(alias_profile)

print(alias_profile.model_dump())

assert alias_profile.skills == [
    "electrical wiring",
    "electrical wiring"
]