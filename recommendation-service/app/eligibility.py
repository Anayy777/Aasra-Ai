from app.models import BeneficiaryProfile, Qualification
from app.special_category import detect_special_categories

EDUCATION_LEVELS = {
    "5th": 1,
    "8th": 2,
    "10th": 3,
    "12th": 4,
    "iti": 4,
    "diploma": 5,
    "graduate": 6,
    "postgraduate": 7,
}


# Rough fallback only.
#
# NSQF level is NOT the same thing as minimum educational
# qualification. It is used only when no official education
# requirement is available.
NSQF_EDUCATION_FALLBACK = {
    1: "5th",
    2: "8th",
    3: "8th",
    4: "10th",
    5: "12th",
    6: "diploma",
    7: "graduate",
    8: "postgraduate",
}


def get_education_level(education):
    """
    Convert normalized education into a comparable level.
    """

    if not education:
        return None

    education = str(education).lower().strip()

    return EDUCATION_LEVELS.get(education)


def get_fallback_education_from_nsqf(nsqf_level):
    """
    Return a rough fallback education level.

    IMPORTANT:
    This is not an official qualification requirement.
    """

    if nsqf_level is None:
        return None

    try:
        level = int(float(nsqf_level))
    except (TypeError, ValueError):
        return None

    return NSQF_EDUCATION_FALLBACK.get(level)


def check_education_eligibility(
    user_education,
    required_education,
):
    """
    Compare user education against an explicitly supplied
    minimum education requirement.
    """

    if not required_education:
        return {
            "eligible": True,
            "source": "unknown",
            "reason": "Minimum education requirement unavailable.",
        }

    user_level = get_education_level(
        user_education
    )

    required_level = get_education_level(
        required_education
    )

    if user_level is None:
        return {
            "eligible": True,
            "source": "unknown",
            "reason": "User education could not be compared.",
        }

    if required_level is None:
        return {
            "eligible": True,
            "source": "unknown",
            "reason": (
                "Qualification education requirement "
                "could not be compared."
            ),
        }

    return {
        "eligible": user_level >= required_level,
        "source": "official",
        "reason": (
            f"User education: {user_education}; "
            f"required: {required_education}."
        ),
    }

def check_special_category_eligibility(
    profile: BeneficiaryProfile,
    qualification: Qualification,
):
    """
    Check whether a qualification targeted at a special
    beneficiary category is applicable to the user.

    Rules:

    1. Qualification with no special category:
       eligible.

    2. Qualification with special category:
       eligible only when the user explicitly has the
       same category.

    3. Missing user category information:
       do not infer it.
       Therefore the special-category qualification
       is not considered applicable.
    """

    qualification_categories = (
        detect_special_categories(
            qualification
        )
    )

    # Normal qualification.
    if not qualification_categories:
        return {
            "eligible": True,
            "source": "not_special_category_specific",
            "reason": (
                "Qualification is not restricted to "
                "a detected special beneficiary category."
            ),
            "qualification_categories": [],
            "matched_categories": [],
        }

    user_categories = {
        str(category).lower().strip()
        for category in profile.special_categories
        if category
    }

    matched_categories = (
        set(qualification_categories)
        & user_categories
    )

    if matched_categories:
        return {
            "eligible": True,
            "source": "explicit_user_category",
            "reason": (
                "User explicitly belongs to a category "
                "targeted by the qualification."
            ),
            "qualification_categories": (
                qualification_categories
            ),
            "matched_categories": sorted(
                matched_categories
            ),
        }

    return {
        "eligible": False,
        "source": "special_category_mismatch",
        "reason": (
            "Qualification is targeted at a special "
            "beneficiary category, but the user has not "
            "explicitly provided a matching category."
        ),
        "qualification_categories": (
            qualification_categories
        ),
        "matched_categories": [],
    }

def check_qualification_eligibility(
    profile: BeneficiaryProfile,
    qualification: Qualification,
    required_education=None,
):
    """
    Check qualification eligibility.

    Priority:

    1. Special-category applicability.
    2. Explicit education requirement, if available.
    3. Otherwise do NOT use NSQF as a hard rejection rule.
    4. Return the NSQF fallback only as informational metadata.

    The cleaned NQR dataset does not contain a dedicated
    minimum-education field. Therefore NSQF is not used
    as a hard education rejection rule.
    """

    # ------------------------------------------------------
    # STEP 0: Special-category applicability
    # ------------------------------------------------------

    special_category_result = (
        check_special_category_eligibility(
            profile,
            qualification,
        )
    )

    # If the qualification is specifically targeted at a
    # category that the user has not explicitly provided,
    # reject it.
    if not special_category_result["eligible"]:
        return {
            **special_category_result,
            "qualification_id": (
                qualification.qualification_id
            ),
            "qualification_title": (
                qualification.title
            ),
        }

    # ------------------------------------------------------
    # STEP 1: Explicit education requirement
    # ------------------------------------------------------

    if required_education:

        education_result = check_education_eligibility(
            profile.education,
            required_education,
        )

        return {
            **education_result,
            "qualification_id": (
                qualification.qualification_id
            ),
            "qualification_title": (
                qualification.title
            ),
            "special_category_source": (
                special_category_result["source"]
            ),
            "special_category_reason": (
                special_category_result["reason"]
            ),
        }

    # ------------------------------------------------------
    # STEP 2: No explicit education requirement
    # ------------------------------------------------------

    fallback_education = (
        get_fallback_education_from_nsqf(
            qualification.nsqf_level
        )
    )

    return {
        "eligible": True,

        # Preserve the fact that special-category
        # applicability was explicitly satisfied.
        "source": (
            special_category_result["source"]
        ),

        "reason": (
            special_category_result["reason"]
        ),

        "qualification_id": (
            qualification.qualification_id
        ),

        "qualification_title": (
            qualification.title
        ),

        "fallback_education": fallback_education,

        "special_category_source": (
            special_category_result["source"]
        ),

        "special_category_reason": (
            special_category_result["reason"]
        ),

        "qualification_categories": (
            special_category_result[
                "qualification_categories"
            ]
        ),

        "matched_categories": (
            special_category_result[
                "matched_categories"
            ]
        ),
    }