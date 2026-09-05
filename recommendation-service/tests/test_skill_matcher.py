import json

from app.skill_matcher import calculate_skill_similarity


# Load courses
with open("data/courses.json", "r", encoding="utf-8") as file:
    courses = json.load(file)


# Beneficiary skills
user_skills = [
    "electrical wiring",
    "maintenance"
]


# Calculate similarity with every course
for course in courses:

    score = calculate_skill_similarity(
        user_skills,
        course["skills"]
    )

    print(
        course["course_id"],
        course["name"],
        "→",
        round(score, 3)
    )
print("\nALIAS MATCHING TEST")

alias_user_skills = [
    "wiring",
    "maintenance"
]

normalized_user_skills = [
    "electrical wiring" if skill == "wiring" else skill
    for skill in alias_user_skills
]

electrician_course = courses[0]

alias_score = calculate_skill_similarity(
    normalized_user_skills,
    electrician_course["skills"]
)

print(
    "Normalized skills:",
    normalized_user_skills
)

print(
    "Electrician similarity:",
    round(alias_score, 3)
)

assert alias_score > 0.7
