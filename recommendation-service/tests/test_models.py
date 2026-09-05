from app.models import BeneficiaryProfile


profile = BeneficiaryProfile(
    education="12th",
    occupation="electrician",
    skills=["electrical work"],
    location="Delhi",
    employment_preference="full_time"
)

print(profile)
print(profile.model_dump())