
import json

from app.models import BeneficiaryProfile
from app.ranker import rank_courses


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
        "max_distance_km": 10
    },
    employment_preference="full_time"
)


# User coordinates
user_latitude = 28.6139
user_longitude = 77.2090


# Rank courses
ranked_courses = rank_courses(
    profile,
    courses,
    user_latitude,
    user_longitude
)


# Print results
for course in ranked_courses:

    print(
        course["course_id"],
        course["course_name"],
        "| Skill:",
        round(course["skill_score"], 3),
        "| Location:",
        round(course["location_score"], 3),
        "| Distance:",
        round(course["distance_km"], 2),
        "km",
        "| Final:",
        round(course["final_score"], 3)
    )