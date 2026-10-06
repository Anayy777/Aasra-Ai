"""Match verified training batches to a beneficiary and an NQR qualification.

The NQR workbook describes qualifications, not available training seats. This
catalogue is deliberately empty until a team member supplies verified batches.
"""

import csv
from datetime import date, timedelta
from pathlib import Path

from app.location import haversine_distance


DEFAULT_CATALOGUE = Path(__file__).resolve().parent.parent / "data" / "training_offerings.csv"


def _optional_float(value):
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def load_training_offerings(path=DEFAULT_CATALOGUE):
    """Read a reviewed batch export; absence means availability is unknown."""
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def match_training_offerings(profile, qualification_id, offerings, latitude=None, longitude=None):
    """Return matching batches, using only supplied locality and access data.

    A missing location or accessibility fact is reported as unknown, never
    presented as a confirmed local or accessible option.
    """
    matches = []
    for offering in offerings:
        if offering.get("qualification_id", "").strip() != qualification_id:
            continue
        if not all(offering.get(key, "").strip() for key in ("batch_id", "centre_name", "provider_name", "source_url")):
            continue
        if offering.get("status", "").strip().lower() != "open":
            continue
        try:
            verified = date.fromisoformat(offering.get("verified_at", "").strip())
        except ValueError:
            continue
        if not date.today() - timedelta(days=30) <= verified <= date.today():
            continue
        start = offering.get("start_date", "").strip()
        if start:
            try:
                if date.fromisoformat(start) < date.today():
                    continue
            except ValueError:
                continue

        distance = None
        centre_lat = _optional_float(offering.get("latitude"))
        centre_lon = _optional_float(offering.get("longitude"))
        if latitude is not None and longitude is not None and centre_lat is not None and centre_lon is not None:
            distance = round(haversine_distance(latitude, longitude, centre_lat, centre_lon), 1)
            limit = profile.mobility.max_distance_km
            if limit is not None and distance > limit:
                continue

        locality_parts = {
            part.strip().casefold()
            for part in (profile.location or "").replace("/", ",").split(",")
            if part.strip()
        }
        district = offering.get("district", "").strip().casefold()
        state = offering.get("state", "").strip().casefold()
        locality_match = bool(locality_parts & {district, state})
        # Without coordinates, require an explicit district/state match.
        if distance is None and not locality_match:
            continue

        pathway = offering.get("employment_pathway", "").strip().lower()
        preference = (profile.employment_preference or "").strip().lower()
        pathway_match = not preference or pathway in {"both", preference}
        accessibility = offering.get("accessibility_confirmed", "").strip().lower()
        if profile.mobility.physical_constraints and accessibility == "no":
            continue

        matches.append({
            "batch_id": offering.get("batch_id", ""),
            "centre_name": offering.get("centre_name", ""),
            "provider_name": offering.get("provider_name", ""),
            "district": offering.get("district", ""),
            "state": offering.get("state", ""),
            "distance_km": distance,
            "start_date": start,
            "enrollment_url": offering.get("enrollment_url", ""),
            "source_url": offering.get("source_url", ""),
            "verified_at": offering.get("verified_at", ""),
            "employment_pathway": pathway or "unknown",
            "preference_match": pathway_match,
            "accessibility": (
                "confirmed" if accessibility == "yes" else "unverified"
            ) if profile.mobility.physical_constraints else "not_requested",
        })

    matches.sort(key=lambda item: (
        not item["preference_match"],
        item["accessibility"] == "unverified",
        item["distance_km"] if item["distance_km"] is not None else float("inf"),
    ))
    return matches
