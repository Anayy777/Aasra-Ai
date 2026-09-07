from app.models import BeneficiaryProfile


# Broad trade families.
# These are used to understand what kind of work the beneficiary does.
TRADE_FAMILIES = {
    "electrician": [
        "electrician",
        "electrical",
        "electric",
        "wiring",
        "wireman",
        "electrical fitter",
        "electrical maintenance",
        "electrical installation",
        "electrical repair",
        "bijli",
        "bijli ka kaam",
        "bijli ki wiring",
    ],
    "plumber": [
        "plumber",
        "plumbing",
        "pipe fitting",
        "pipe fitter",
        "sanitary",
        "water supply",
    ],
    "carpenter": [
        "carpenter",
        "carpentry",
        "wood work",
        "woodworking",
        "furniture",
    ],
    "welder": [
        "welder",
        "welding",
        "fabrication",
        "metal fabrication",
    ],
    "computer_hardware": [
        "computer hardware",
        "hardware technician",
        "computer repair",
        "laptop repair",
        "desktop repair",
        "hardware maintenance",
    ],
    "automotive": [
        "automobile",
        "automotive",
        "car mechanic",
        "vehicle mechanic",
        "motor mechanic",
        "auto mechanic",
        "automobile repair",
    ],
}


# Specializations are deliberately limited to domains that
# can be meaningfully inferred from the beneficiary's text.
SPECIALIZATIONS = {
    "electrician": {
        "industrial": [
            "industrial",
            "factory",
            "motor",
            "transformer",
            "control panel",
            "industrial maintenance",
            "industrial wiring",
        ],
        "telecom": [
            "telecom",
            "telecommunication",
            "cell site",
            "mobile tower",
            "tower",
        ],
        "construction": [
            "construction",
            "construction site",
            "building",
            "residential wiring",
            "house wiring",
            "domestic wiring",
        ],
        "power_distribution": [
            "power distribution",
            "power transmission",
            "lineman",
            "line maintenance",
            "power supply",
            "distribution line",
            "electric grid",
        ],
        "mine": [
            "mine",
            "mining",
            "opencast",
            "underground mine",
        ],
        "oil_gas": [
            "oil",
            "oil and gas",
            "gas",
            "petroleum",
            "refinery",
            "refineries",
        ],
        "smart": [
            "smart electrician",
            "smart electrical",
            "smart home",
            "home automation",
        ],
        "solar": [
            "solar",
            "solar pv",
            "photovoltaic",
            "solar panel",
        ],
    }
}


def normalize_text(value):
    """Normalize text for classification."""
    if not value:
        return ""

    return str(value).lower().strip()


def build_profile_text(profile: BeneficiaryProfile):
    """
    Combine occupation and skills into one searchable text.

    Location and education are intentionally excluded because
    they do not determine the trade family.
    """

    parts = []

    if profile.occupation:
        parts.append(profile.occupation)

    parts.extend(
        skill
        for skill in profile.skills
        if skill
    )

    return normalize_text(" ".join(parts))


def detect_trade_families(text):
    """
    Return all trade families detected in the profile text.
    """

    matches = []

    for family, keywords in TRADE_FAMILIES.items():

        for keyword in keywords:

            if keyword in text:
                matches.append(family)
                break

    return matches


def detect_specializations(
    trade_family,
    text,
):
    """
    Detect specializations belonging to the detected trade family.
    """

    if trade_family not in SPECIALIZATIONS:
        return []

    detected = []

    specialization_map = SPECIALIZATIONS[
        trade_family
    ]

    for specialization, keywords in specialization_map.items():

        for keyword in keywords:

            if keyword in text:
                detected.append(specialization)
                break

    return detected


def classify_trade(profile: BeneficiaryProfile):
    """
    Classify a beneficiary into a broad trade family
    and optional specializations.

    Returns:
        {
            "trade_family": str | None,
            "trade_families": list[str],
            "specializations": list[str]
        }
    """

    text = build_profile_text(profile)

    if not text:
        return {
            "trade_family": None,
            "trade_families": [],
            "specializations": [],
        }

    trade_families = detect_trade_families(text)

    # Primary trade family.
    #
    # For the current MVP we use the first detected family.
    # The complete list is still returned for transparency.
    trade_family = (
        trade_families[0]
        if trade_families
        else None
    )

    specializations = detect_specializations(
        trade_family,
        text,
    )

    return {
        "trade_family": trade_family,
        "trade_families": trade_families,
        "specializations": specializations,
    }