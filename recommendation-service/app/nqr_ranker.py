from app.eligibility import check_qualification_eligibility
from app.nqr_matcher import match_qualifications
from app.nqr_normalizer import normalize_text
from app.trade_classifier import classify_trade


# ---------------------------------------------------------
# Final ranking weights
# ---------------------------------------------------------
#
# Relevance = how strongly the qualification matches
#             the beneficiary's actual work/profile.
#
# Specificity = whether the qualification is a direct,
#               sensible choice instead of a loosely related
#               specialization.
#
RELEVANCE_WEIGHT = 0.75
SPECIFICITY_WEIGHT = 0.25


def _is_eligible(profile, qualification):
    """
    Use the existing eligibility engine as a hard filter.
    """

    result = check_qualification_eligibility(
        profile,
        qualification,
    )

    if isinstance(result, bool):
        return result

    if isinstance(result, dict):
        return result.get("eligible", False)

    return bool(result)


def _is_generic_trade_qualification(
    profile,
    qualification,
):
    """
    Determine whether a qualification is a generic/direct
    qualification for the user's trade.

    Example:

        User: Electrician

        "ELECTRICIAN"
            -> generic/direct

        "Telecom Electrician"
            -> specialized

        "Mine Electrician"
            -> specialized

        "Electrician Power Distribution"
            -> specialized
    """

    trade_info = classify_trade(profile)

    trade_family = trade_info.get(
        "trade_family"
    )

    if not trade_family:
        return False

    title = normalize_text(
        qualification.title
    )

    if not title:
        return False

    generic_titles = {
        "electrician": {
            "electrician",
        },
        "plumber": {
            "plumber",
        },
        "carpenter": {
            "carpenter",
        },
        "welder": {
            "welder",
        },
        "computer_hardware": {
            "computer hardware technician",
            "computer hardware",
        },
        "automotive": {
            "automobile mechanic",
            "automotive mechanic",
            "motor mechanic",
        },
    }

    return title in generic_titles.get(
        trade_family,
        set(),
    )


def _has_user_specialization(profile):
    """
    Check whether the beneficiary has enough information
    to justify recommending a specialized qualification.
    """

    trade_info = classify_trade(profile)

    return bool(
        trade_info.get(
            "specializations",
            [],
        )
    )


def _calculate_specificity_score(
    profile,
    qualification,
    match,
):
    """
    Calculate how specifically the qualification fits
    the beneficiary.

    Generic/direct qualifications receive a strong signal
    when the user has no specialization.

    Specialized qualifications receive a strong signal only
    when the user actually has that specialization.
    """

    generic = _is_generic_trade_qualification(
        profile,
        qualification,
    )

    user_has_specialization = (
        _has_user_specialization(profile)
    )

    occupation_score = match.get(
        "occupation_score",
        0.0,
    )

    title_score = match.get(
        "title_score",
        0.0,
    )

    specialization_score = match.get(
        "specialization_score",
        0.0,
    )

    # -----------------------------------------------------
    # General trade user
    # -----------------------------------------------------

    if not user_has_specialization:

        if generic:
            # Strongly prefer direct generic qualification.
            return 1.0

        # A specialized qualification without evidence from
        # the user should not be preferred over a generic one.
        if qualification.specializations:
            return 0.15

        return (
            0.60 * title_score
            + 0.40 * occupation_score
        )

    # -----------------------------------------------------
    # Specialized user
    # -----------------------------------------------------

    if specialization_score >= 1.0:
        return 1.0

    if generic:
        # Generic qualification is still relevant, but the
        # user's specialization should be preferred.
        return 0.65

    return (
        0.50 * title_score
        + 0.30 * occupation_score
        + 0.20 * specialization_score
    )


def _apply_instructor_handling(
    score,
    profile,
    qualification,
):
    """
    Handle instructor/trainer qualifications carefully.

    They are not automatically deleted because the dataset
    explicitly identifies them, but for a normal beneficiary
    seeking employment they should rank below standard
    occupational qualifications.

    If the user explicitly indicates teaching/training work,
    the penalty can be avoided.
    """

    preference_text = " ".join(
        [
            profile.occupation or "",
            *profile.skills,
        ]
    ).lower()

    trainer_keywords = [
        "trainer",
        "training",
        "instructor",
        "teacher",
        "teaching",
        "craft instructor",
        "skill trainer",
    ]

    wants_training_role = any(
        keyword in preference_text
        for keyword in trainer_keywords
    )

    if (
        qualification.is_instructor_or_trainer
        and not wants_training_role
    ):
        return score * 0.35

    return score


def rank_qualifications(
    profile,
    qualifications,
    top_k=3,
):
    """
    Complete NQR qualification ranking pipeline.

    Pipeline:

        NQR qualifications
              ↓
        eligibility filter
              ↓
        relevance matching
              ↓
        generic/specialized logic
              ↓
        instructor handling
              ↓
        final score
              ↓
        deterministic sorting
              ↓
        top_k
    """

    if top_k < 1:
        return []

    matches = match_qualifications(
        profile,
        qualifications,
    )

    ranked = []

    for match in matches:

        qualification = match[
            "qualification"
        ]

        # -------------------------------------------------
        # 1. Eligibility
        # -------------------------------------------------

        if not _is_eligible(
            profile,
            qualification,
        ):
            continue

        # -------------------------------------------------
        # 2. Relevance
        # -------------------------------------------------

        relevance_score = match.get(
            "relevance_score",
            0.0,
        )

        # -------------------------------------------------
        # 3. Specificity
        # -------------------------------------------------

        specificity_score = (
            _calculate_specificity_score(
                profile,
                qualification,
                match,
            )
        )

        # -------------------------------------------------
        # 4. Combine
        # -------------------------------------------------

        final_score = (
            RELEVANCE_WEIGHT
            * relevance_score
            + SPECIFICITY_WEIGHT
            * specificity_score
        )

        # -------------------------------------------------
        # 5. Instructor/trainer handling
        # -------------------------------------------------

        final_score = _apply_instructor_handling(
            final_score,
            profile,
            qualification,
        )

        ranked.append(
            {
                **match,
                "specificity_score": round(
                    specificity_score,
                    4,
                ),
                "final_score": round(
                    final_score,
                    4,
                ),
            }
        )

    # -----------------------------------------------------
    # Deterministic ranking
    # -----------------------------------------------------

    ranked.sort(
        key=lambda item: (
            item["final_score"],
            item["relevance_score"],
            item["specificity_score"],
            item["occupation_score"],
            item["title_score"],
        ),
        reverse=True,
    )

    return ranked[:top_k]