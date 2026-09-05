import json


with open("data/courses.json", "r", encoding="utf-8") as file:
    courses = json.load(file)


print("Number of courses:", len(courses))

for course in courses:
    print(
        course["course_id"],
        "→",
        course["name"]
    )

print("\nCOURSE SCHEMA TEST")

required_fields = [
    "course_id",
    "name",
    "description",
    "skills",
    "education_requirement",
    "employment_type",
    "location",
    "latitude",
    "longitude"
]

for course in courses:

    for field in required_fields:
        assert field in course, (
            f"{course.get('course_id', 'UNKNOWN')} "
            f"is missing field: {field}"
        )

    assert isinstance(course["skills"], list)
    assert isinstance(course["employment_type"], list)

print("All courses passed schema validation.")