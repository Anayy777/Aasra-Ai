from app.models import Qualification


SPECIAL_CATEGORY_KEYWORDS = {
    "divyangjan": [
        "divyangjan",
        "divyang",
        "persons with disability",
        "person with disability",
        "pwd",
    ],
}


def normalize_text(value):
    """
    Normalize text for special-category detection.
    """

    if not value:
        return ""

    return str(value).lower().strip()


def detect_special_categories(
    qualification: Qualification,
):
    """
    Detect special beneficiary categories associated
    with a qualification.

    Detection is based only on information present in
    the NQR qualification.
    """

    searchable_text = " ".join(
        [
            qualification.title or "",
            qualification.description or "",
            qualification.sector or "",
        ]
    )

    searchable_text = normalize_text(
        searchable_text
    )

    detected = []

    for category, keywords in SPECIAL_CATEGORY_KEYWORDS.items():

        for keyword in keywords:

            if keyword in searchable_text:
                detected.append(category)
                break

    return detected