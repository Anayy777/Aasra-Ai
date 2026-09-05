def normalize_education(education):
    if not education:
        return None

    education = education.lower().strip()

    if "12" in education:
        return "12th"

    if "10" in education:
        return "10th"

    if "8" in education:
        return "8th"

    if "5" in education:
        return "5th"

    if "postgraduate" in education or "post graduate" in education:
        return "postgraduate"

    if "graduate" in education:
        return "graduate"

    return education


def normalize_occupation(occupation):
    if not occupation:
        return None

    occupation = occupation.lower().strip()

    return occupation

def normalize_skill(skill):
    if not skill:
        return None

    skill = skill.lower().strip()

    skill_aliases = {
        "wiring": "electrical wiring",
        "electrical work": "electrical wiring",
        "bijli ka kaam": "electrical wiring",
        "bijli ki wiring": "electrical wiring",
    }

    return skill_aliases.get(skill, skill)


def normalize_employment_preference(preference):
    if not preference:
        return None

    preference = preference.lower().strip()

    if "full" in preference:
        return "full_time"

    if "part" in preference:
        return "part_time"

    return preference


def normalize_profile(profile):
    profile.education = normalize_education(profile.education)

    profile.occupation = normalize_occupation(profile.occupation)

    profile.employment_preference = normalize_employment_preference(
        profile.employment_preference
    )

    profile.skills = [
    normalize_skill(skill)
    for skill in profile.skills
   ]

    if profile.location:
        profile.location = profile.location.strip()

    return profile