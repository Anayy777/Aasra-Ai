from app.models import BeneficiaryProfile, Qualification
from app.nqr_normalizer import (
    get_normalized_qualification_text,
    normalize_text,
)
from app.trade_classifier import classify_trade


# Weights used to calculate qualification relevance.
#
# Title is strongest because the qualification name is the
# clearest signal of what the course actually is.
TITLE_WEIGHT = 0.30
OCCUPATION_WEIGHT = 0.25
SKILL_WEIGHT = 0.20
TRADE_WEIGHT = 0.15
SPECIALIZATION_WEIGHT = 0.10


def _contains_phrase(text, phrase):
    """
    Check whether a complete normalized phrase exists in text.

    Example:
        'solar lighting assembler'
        does NOT match the occupation
        'electrician' merely because of unrelated substring noise.
    """

    if not text or not phrase:
        return False

    text_words = set(text.split())
    phrase_words = phrase.split()

    if len(phrase_words) == 1:
        return phrase_words[0] in text_words

    return phrase in text


def _best_keyword_match(user_terms, qualification_terms):
    """
    Calculate the proportion of user terms that have a meaningful
    match in qualification terms.

    Returns a value between 0 and 1.
    """

    if not user_terms or not qualification_terms:
        return 0.0

    matched = 0

    for user_term in user_terms:

        for qualification_term in qualification_terms:

            if (
                _contains_phrase(qualification_term, user_term)
                or _contains_phrase(user_term, qualification_term)
            ):
                matched += 1
                break

    return matched / len(user_terms)


def calculate_title_score(
    profile: BeneficiaryProfile,
    qualification: Qualification,
    normalized_data: dict,
):
    """
    Score how closely the qualification title matches
    the beneficiary's occupation and skills.
    """

    title = normalized_data["title"]

    if not title:
        return 0.0

    occupation = normalize_text(
        profile.occupation
    )

    if occupation and _contains_phrase(title, occupation):
        return 1.0

    occupation_words = (
        occupation.split()
        if occupation
        else []
    )

    if occupation_words:

        matched_words = sum(
            1
            for word in occupation_words
            if word in set(title.split())
        )

        if matched_words:
            return matched_words / len(occupation_words)

    # Skills can also provide a title signal.
    skill_score = _best_keyword_match(
        [
            normalize_text(skill)
            for skill in profile.skills
            if normalize_text(skill)
        ],
        [title],
    )

    return skill_score


def calculate_occupation_score(
    profile: BeneficiaryProfile,
    qualification: Qualification,
    normalized_data: dict,
):
    """
    Compare beneficiary occupation with NQR proposed occupations.

    Exact/phrase matching is preferred over loose substring matching.
    """

    user_occupation = normalize_text(
        profile.occupation
    )

    occupations = normalized_data[
        "proposed_occupations"
    ]

    if not user_occupation or not occupations:
        return 0.0

    # Exact occupation match.
    if user_occupation in occupations:
        return 1.0

    # Phrase-level match.
    for occupation in occupations:

        if (
            _contains_phrase(
                occupation,
                user_occupation,
            )
            or _contains_phrase(
                user_occupation,
                occupation,
            )
        ):
            return 0.85

    # Compare individual words only when they are meaningful.
    user_words = set(user_occupation.split())

    if not user_words:
        return 0.0

    best_score = 0.0

    for occupation in occupations:

        occupation_words = set(
            occupation.split()
        )

        if not occupation_words:
            continue

        overlap = len(
            user_words & occupation_words
        )

        score = overlap / len(user_words)

        best_score = max(
            best_score,
            score,
        )

    return best_score


def calculate_skill_score(
    profile: BeneficiaryProfile,
    qualification: Qualification,
    normalized_data: dict,
):
    """
    Match beneficiary skills against searchable qualification
    fields available in the cleaned NQR dataset.

    The current cleaned dataset does not contain a dedicated
    qualification-skills column, so title, occupation and
    description are used as skill evidence.
    """

    user_skills = [
        normalize_text(skill)
        for skill in profile.skills
        if normalize_text(skill)
    ]

    if not user_skills:
        return 0.0

    searchable_text = " ".join(
        [
            normalized_data["title"],
            normalized_data["description"],
            " ".join(
                normalized_data[
                    "proposed_occupations"
                ]
            ),
        ]
    )

    if not searchable_text:
        return 0.0

    matched = 0

    words = set(
        searchable_text.split()
    )

    for skill in user_skills:

        if _contains_phrase(
            searchable_text,
            skill,
        ):
            matched += 1
            continue

        skill_words = skill.split()

        if any(
            word in words
            for word in skill_words
            if len(word) > 2
        ):
            matched += 1

    return matched / len(user_skills)


def calculate_trade_score(
    trade_info,
    qualification: Qualification,
    normalized_data: dict,
):
    """
    Compare beneficiary trade family with qualification data.
    """

    trade_family = trade_info.get(
        "trade_family"
    )

    if not trade_family:
        return 0.0

    searchable_text = " ".join(
        [
            normalized_data["title"],
            " ".join(
                normalized_data[
                    "proposed_occupations"
                ]
            ),
            normalized_data["sector"],
            normalized_data["description"],
        ]
    )

    trade_keywords = {
        "electrician": [
            "electrician",
            "electrical",
            "wireman",
            "wiring",
            "electrical fitter",
        ],
        "plumber": [
            "plumber",
            "plumbing",
            "pipe fitting",
            "sanitary",
        ],
        "carpenter": [
            "carpenter",
            "carpentry",
            "woodworking",
            "furniture",
        ],
        "welder": [
            "welder",
            "welding",
            "fabrication",
        ],
        "computer_hardware": [
            "computer hardware",
            "hardware technician",
            "computer repair",
        ],
        "automotive": [
            "automobile",
            "automotive",
            "vehicle mechanic",
            "motor mechanic",
        ],
    }

    keywords = trade_keywords.get(
        trade_family,
        [],
    )

    if not keywords:
        return 0.0

    matched = sum(
        1
        for keyword in keywords
        if _contains_phrase(
            searchable_text,
            normalize_text(keyword),
        )
    )

    if matched == 0:
        return 0.0

    return min(
        1.0,
        matched / 2,
    )


def calculate_specialization_score(
    trade_info,
    qualification: Qualification,
    normalized_data: dict,
):
    """
    Score specialization compatibility.

    Important:
    If the beneficiary has no detected specialization,
    we do NOT give every qualification a perfect score.
    """

    user_specializations = set(
        trade_info.get(
            "specializations",
            [],
        )
    )

    qualification_specializations = set(
        normalized_data[
            "specializations"
        ]
    )

    # No specialization known for the user.
    #
    # Generic qualifications should remain neutral rather
    # than being artificially rewarded.
    if not user_specializations:
        if not qualification_specializations:
            return 0.5

        return 0.0

    if not qualification_specializations:
        return 0.0

    overlap = (
        user_specializations
        & qualification_specializations
    )

    if overlap:
        return 1.0

    return 0.0


def calculate_relevance_score(
    profile: BeneficiaryProfile,
    qualification: Qualification,
):
    """
    Calculate the raw relevance score for one qualification.
    """

    normalized_data = (
        get_normalized_qualification_text(
            qualification
        )
    )

    trade_info = classify_trade(
        profile
    )

    title_score = calculate_title_score(
        profile,
        qualification,
        normalized_data,
    )

    occupation_score = (
        calculate_occupation_score(
            profile,
            qualification,
            normalized_data,
        )
    )

    skill_score = calculate_skill_score(
        profile,
        qualification,
        normalized_data,
    )

    trade_score = calculate_trade_score(
        trade_info,
        qualification,
        normalized_data,
    )

    specialization_score = (
        calculate_specialization_score(
            trade_info,
            qualification,
            normalized_data,
        )
    )

    final_score = (
        TITLE_WEIGHT * title_score
        + OCCUPATION_WEIGHT * occupation_score
        + SKILL_WEIGHT * skill_score
        + TRADE_WEIGHT * trade_score
        + SPECIALIZATION_WEIGHT
        * specialization_score
    )

    return {
        "title_score": round(
            title_score,
            4,
        ),
        "occupation_score": round(
            occupation_score,
            4,
        ),
        "skill_score": round(
            skill_score,
            4,
        ),
        "trade_score": round(
            trade_score,
            4,
        ),
        "specialization_score": round(
            specialization_score,
            4,
        ),
        "relevance_score": round(
            final_score,
            4,
        ),
    }


def match_qualification(
    profile: BeneficiaryProfile,
    qualification: Qualification,
):
    """
    Match one NQR qualification against a beneficiary.

    Returns the qualification together with detailed
    matching signals.
    """

    scores = calculate_relevance_score(
        profile,
        qualification,
    )

    return {
        "qualification": qualification,
        **scores,
    }


def match_qualifications(
    profile: BeneficiaryProfile,
    qualifications: list[Qualification],
):
    """
    Match a beneficiary against all supplied qualifications.

    No ranking happens here.
    Ranking is handled separately by nqr_ranker.py.
    """

    matches = []

    for qualification in qualifications:

        matches.append(
            match_qualification(
                profile,
                qualification,
            )
        )

    return matches