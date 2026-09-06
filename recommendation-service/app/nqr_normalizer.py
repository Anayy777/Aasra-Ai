import re
import unicodedata

from app.models import Qualification


def normalize_text(value):
    """
    Normalize text for reliable matching.

    Example:
        'Electrical  Wiring' -> 'electrical wiring'
        'Oil & Gas'          -> 'oil and gas'
    """
    if not value:
        return ""

    text = str(value)

    # Normalize Unicode characters.
    text = unicodedata.normalize("NFKC", text)

    # Convert to lowercase.
    text = text.lower()

    # Treat ampersand as the word "and".
    text = text.replace("&", " and ")

    # Replace separators/punctuation with spaces.
    text = re.sub(r"[^a-z0-9]+", " ", text)

    # Collapse repeated whitespace.
    text = re.sub(r"\s+", " ", text).strip()

    return text


def normalize_list(values):
    """
    Normalize every value in a list.
    """
    if not values:
        return []

    normalized = []

    for value in values:
        text = normalize_text(value)

        if text:
            normalized.append(text)

    return normalized


def normalize_qualification(
    qualification: Qualification,
) -> Qualification:
    """
    Create a normalized Qualification object for matching.

    The original qualification object is not modified.
    """

    return Qualification(
        qualification_id=qualification.qualification_id,

        title=qualification.title,

        description=qualification.description,

        sector=qualification.sector,

        nsqf_level=qualification.nsqf_level,

        qualification_type=qualification.qualification_type,

        proposed_occupation=list(
            qualification.proposed_occupation
        ),

        skills=list(
            qualification.skills
        ),

        progression_pathway=qualification.progression_pathway,

        status=qualification.status,

        is_instructor_or_trainer=(
            qualification.is_instructor_or_trainer
        ),

        specializations=list(
            qualification.specializations
        ),

        data_quality_flags=list(
            qualification.data_quality_flags
        ),
    )


def get_normalized_qualification_text(
    qualification: Qualification,
) -> dict:
    """
    Return normalized searchable fields.

    These values are used by the NQR matching engine.
    """

    return {
        "title": normalize_text(
            qualification.title
        ),

        "description": normalize_text(
            qualification.description
        ),

        "sector": normalize_text(
            qualification.sector
        ),

        "proposed_occupations": normalize_list(
            qualification.proposed_occupation
        ),

        "specializations": normalize_list(
            qualification.specializations
        ),

        "progression_pathway": normalize_text(
            qualification.progression_pathway
        ),

        "qualification_type": normalize_text(
            qualification.qualification_type
        ),

        "data_quality_flags": normalize_list(
            qualification.data_quality_flags
        ),
    }