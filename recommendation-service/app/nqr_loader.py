from pathlib import Path

import pandas as pd

from app.models import Qualification


DEFAULT_FILE = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "Aasra_NQR_Cleaned.xlsx"
)

DEFAULT_SHEET = "active_qualifications"


def _clean_text(value):
    """Return a clean string or None."""
    if value is None:
        return None

    if pd.isna(value):
        return None

    text = str(value).strip()

    return text if text else None


def _parse_float(value):
    """Convert numeric Excel values safely."""
    if value is None or pd.isna(value):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_list(value):
    """
    Parse cleaned Excel list fields.

    The cleaned dataset stores multiple values using:
        value1 | value2 | value3
    """
    text = _clean_text(value)

    if not text:
        return []

    return [
        item.strip()
        for item in text.split("|")
        if item.strip()
    ]


def _parse_bool(value):
    """Convert cleaned boolean values safely."""
    if isinstance(value, bool):
        return value

    text = _clean_text(value)

    if not text:
        return False

    return text.lower() in {
        "true",
        "1",
        "yes",
        "y",
    }


def load_nqr_qualifications(
    file_path=None,
    sheet_name=DEFAULT_SHEET,
):
    """
    Load qualifications from Aasra_NQR_Cleaned.xlsx.

    By default:
        data/Aasra_NQR_Cleaned.xlsx
        sheet: active_qualifications

    Returns:
        list[Qualification]
    """

    path = Path(file_path) if file_path else DEFAULT_FILE

    if not path.exists():
        raise FileNotFoundError(
            f"NQR dataset not found: {path}"
        )

    dataframe = pd.read_excel(
        path,
        sheet_name=sheet_name,
    )

    required_columns = {
        "qualification_id",
        "title",
        "description",
        "sector",
        "nsqf_level",
        "proposed_occupations",
        "progression_pathway",
        "qualification_type",
        "status_as_of_2026_09_06",
        "is_instructor_or_trainer",
        "specializations",
        "data_quality_flags",
    }

    missing_columns = required_columns - set(dataframe.columns)

    if missing_columns:
        raise ValueError(
            "NQR dataset is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    qualifications = []

    for _, row in dataframe.iterrows():

        title = _clean_text(row["title"])

        # A qualification without a title is unusable.
        if not title:
            continue

        qualification = Qualification(
            qualification_id=(
                _clean_text(row["qualification_id"]) or ""
            ),

            title=title,

            description=_clean_text(
                row["description"]
            ),

            sector=_clean_text(
                row["sector"]
            ),

            nsqf_level=_parse_float(
                row["nsqf_level"]
            ),

            qualification_type=_clean_text(
                row["qualification_type"]
            ),

            proposed_occupation=_parse_list(
                row["proposed_occupations"]
            ),

            skills=[],

            progression_pathway=_clean_text(
                row["progression_pathway"]
            ),

            status=_clean_text(
                row["status_as_of_2026_09_06"]
            ),

            is_instructor_or_trainer=_parse_bool(
                row["is_instructor_or_trainer"]
            ),

            specializations=_parse_list(
                row["specializations"]
            ),

            data_quality_flags=_parse_list(
                row["data_quality_flags"]
            ),
        )

        qualifications.append(qualification)

    return qualifications