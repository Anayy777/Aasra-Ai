"""
Guided conversation state machine.

Each WhatsApp phone number gets its own "session" that tracks:
  - what language they're speaking (detected from their first message)
  - which profile question they're currently on
  - the answers collected so far
"""

PROFILE_STEPS = [
    ("name", "What is your name?"),
    ("location", "Which village, town or district do you live in?"),
    ("education", "What is your educational background?"),
    ("family_occupation", "What work does your family traditionally do?"),
    ("current_livelihood", "What do you currently do for work, if anything?"),
    ("skills_interest", "What skills do you have, or what would you like to learn?"),
    ("mobility", "Do you have any travel or physical constraints we should know about?"),
    ("employment_preference", "Would you prefer to start your own work, or work for someone else?"),
]

FIELD_ALIASES = {
    "name": ["name"],
    "location": ["location", "village", "district", "town", "place"],
    "education": ["education", "school", "study", "studies"],
    "family_occupation": ["family", "family occupation", "family work"],
    "current_livelihood": ["current work", "current job", "livelihood", "work now"],
    "skills_interest": ["skill", "interest", "learn"],
    "mobility": ["mobility", "travel", "constraint", "disability"],
    "employment_preference": ["employment", "self employment", "job preference", "self-employed", "wage"],
}

# session states
COLLECTING = "COLLECTING"
CONFIRMING = "CONFIRMING"
EDITING_SINGLE = "EDITING_SINGLE"
DONE = "DONE"

import json
import sqlite3

# Sessions are persisted to SQLite instead of a plain in-memory dict.
DB_PATH = "sessions.db"


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            phone_number TEXT PRIMARY KEY,
            session_json TEXT NOT NULL
        )
    """)
    return conn


def get_session(phone_number: str):
    """Returns the existing session for this number, or None if it's a
    brand new conversation."""
    conn = _get_db()
    row = conn.execute(
        "SELECT session_json FROM sessions WHERE phone_number = ?", (phone_number,)
    ).fetchone()
    conn.close()
    return json.loads(row[0]) if row else None


def _save_session(phone_number: str, session: dict):
    conn = _get_db()
    conn.execute(
        "INSERT OR REPLACE INTO sessions (phone_number, session_json) VALUES (?, ?)",
        (phone_number, json.dumps(session)),
    )
    conn.commit()
    conn.close()


def create_session(phone_number: str, language_code: str):
    """Starts a fresh profile-building session for a new user."""
    session = {
        "language": language_code,
        "state": COLLECTING,
        "step_index": 0,
        "profile": {},
        "editing_field": None,
    }
    _save_session(phone_number, session)
    return session


def save_session(phone_number: str, session: dict):
    """Call this after mutating a session dict in place (changing state,
    advancing step_index, adding a profile answer, etc.) -- otherwise the
    change only exists in memory for this request and is lost."""
    _save_session(phone_number, session)


def reset_session(phone_number: str):
    conn = _get_db()
    conn.execute("DELETE FROM sessions WHERE phone_number = ?", (phone_number,))
    conn.commit()
    conn.close()


def current_question(session) -> str:
    """The question text for whatever step the session is currently on."""
    field_key, question = PROFILE_STEPS[session["step_index"]]
    return question


def current_field(session) -> str:
    field_key, _ = PROFILE_STEPS[session["step_index"]]
    return field_key


def is_last_step(session) -> bool:
    return session["step_index"] >= len(PROFILE_STEPS) - 1


def advance_step(session):
    session["step_index"] += 1


def build_profile_summary(profile: dict) -> str:
    """Human-readable summary shown/spoken back for confirmation."""
    lines = ["Here is what I understood about you:"]
    labels = {
        "name": "Name",
        "location": "Location",
        "education": "Education",
        "family_occupation": "Family occupation",
        "current_livelihood": "Current work",
        "skills_interest": "Skills/interests",
        "mobility": "Mobility",
        "employment_preference": "Preference",
    }
    for field_key, _ in PROFILE_STEPS:
        value = profile.get(field_key, "-")
        lines.append(f"{labels[field_key]}: {value}")
    lines.append("Reply 'confirm' if this is correct, or say 'edit' and the "
                  "field you want to change, e.g. 'edit location'.")
    return "\n".join(lines)


def match_edit_field(text: str):
    """Looks for an edit request like 'edit location' or 'change my name'
    in free-form text, returns the matching field_key or None."""
    text_lower = text.lower()
    if "edit" not in text_lower and "change" not in text_lower:
        return None
    for field_key, keywords in FIELD_ALIASES.items():
        for kw in keywords:
            if kw in text_lower:
                return field_key
    return None


def is_confirmation(text: str) -> bool:
    text_lower = text.lower().strip()
    return any(word in text_lower for word in ["confirm", "yes", "correct", "haan", "sahi"])