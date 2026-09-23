def format_recommendation_reply(
    result,
    language_code=None,
):
    """
    Convert NQR recommendation results into a
    human-readable response.

    Currently supports Hindi/Hinglish style output.
    Language-specific response generation can be
    expanded later.
    """

    recommendations = result.get(
        "recommendations",
        [],
    )

    if not recommendations:
        return (
            "Aapke profile ke liye abhi koi "
            "suitable qualification nahi mili."
        )

    lines = [
        "Aapke profile ke hisaab se ye qualifications "
        "suitable hain:\n"
    ]

    for index, qualification in enumerate(
        recommendations,
        start=1,
    ):

        title = qualification.get(
            "qualification_title",
            "Unknown qualification",
        )

        final_score = qualification.get(
            "final_score",
            0.0,
        )

        match_percentage = round(
            final_score * 100
        )

        nsqf_level = qualification.get(
            "nsqf_level"
        )

        sector = qualification.get(
            "sector"
        )

        proposed_occupations = qualification.get(
            "proposed_occupations",
            [],
        )

        progression_pathway = qualification.get(
            "progression_pathway"
        )

        lines.append(
            f"{index}. {title}"
        )

        lines.append(
            f"   Match: {match_percentage}%"
        )

        if nsqf_level is not None:
            lines.append(
                f"   NSQF Level: {nsqf_level}"
            )

        if sector:
            lines.append(
                f"   Sector: {sector}"
            )

        if proposed_occupations:
            occupations = ", ".join(
                proposed_occupations[:3]
            )

            lines.append(
                f"   Related roles: {occupations}"
            )

        if progression_pathway:
            lines.append(
                f"   Progression: "
                f"{progression_pathway}"
            )

        options = qualification.get("training_options", [])
        if options:
            option = options[0]
            lines.append(
                f"   Verified batch: {option['centre_name']} ({option['district']}, "
                f"{option['state']}), starts {option['start_date'] or 'date to confirm'}"
            )
            if option["distance_km"] is not None:
                lines.append(f"   Distance: {option['distance_km']} km")
            if option["accessibility"] == "unverified":
                lines.append("   Accessibility: confirm with the centre")
            if option["batch_id"]:
                lines.append(f"   Batch ID: {option['batch_id']}")
            if option["enrollment_url"]:
                lines.append(
                    f"   Batch link (sign in and complete e-KYC first if needed): "
                    f"{option['enrollment_url']}"
                )
        else:
            lines.append("   No verified local training batch is listed yet.")
        lines.append("")

    lines.extend([
        "To look for a PMKVY training batch, open Skill India Digital: "
        "https://www.skillindiadigital.gov.in/home",
        "Register if you are new, or log in. Complete e-KYC if it is pending. "
        "Then search the recommended job role, check the scheme and batch ID, "
        "and submit your interest. The centre must approve it before enrollment.",
    ])
    return "\n".join(lines)