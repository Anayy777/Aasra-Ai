import json

from app.models import BeneficiaryProfile
from app.matcher import is_eligible


# Load courses
with open("data/courses.json", "r", encoding="utf-8") as file:
    courses = json.load(file)


# Beneficiary profile
profile = BeneficiaryProfile(
    education="12th",
    occupation="electrician",
    skills=[
        "electrical wiring",
        "maintenance"
    ],
    location="Delhi",
    mobility={
        "max_distance_km": 1
    },
    employment_preference="full_time"
)


# User's coordinates
user_latitude = 28.6139
user_longitude = 77.2090


# Check every course
for course in courses:

    eligible = is_eligible(
        profile,
        course,
        user_latitude,
        user_longitude
    )

    print(
        course["course_id"],
        course["name"],
        "→",
        "ELIGIBLE" if eligible else "NOT ELIGIBLE"
    )