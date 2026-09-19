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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recommendation-service"))
from app.nlu import client  # reuse the already-configured Groq client

# Sessions are persisted to SQLite instead of a plain in-memory dict.
DB_PATH = "sessions.db"

FIELD_LABELS = {
    "name": "Name",
    "location": "Location",
    "education": "Education",
    "family_occupation": "Family occupation",
    "current_livelihood": "Current work",
    "skills_interest": "Skills/interests",
    "mobility": "Mobility",
    "employment_preference": "Preference",
}

REQUIRED_FIELDS = [field_key for field_key, _ in PROFILE_STEPS]


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


def get_missing_fields(profile: dict) -> list:
    """Deterministic check -- this is what actually guarantees every
    PS-required field gets collected, regardless of how naturally or
    unpredictably the conversation flows to get there."""
    return [f for f in REQUIRED_FIELDS if not profile.get(f)]


def extract_and_merge(profile: dict, transcript: str) -> dict:
    """
    THE CORE FIX: instead of blindly saving the transcript into whatever
    field the fixed script happened to be on, this asks an LLM to pull
    out ANY of our 8 profile fields present in what the person actually
    said -- so someone who volunteers several things in one sentence
    gets all of them captured, not just one.

    Returns the merged profile. Only overwrites a field if the LLM found
    new information for it -- never blanks out something already known,
    even if this call fails or the model omits a field.
    """
    try:
        prompt = f"""You are having a warm, natural conversation with a
beneficiary of a government skilling scheme to understand their
background. Extract ONLY the information that is EXPLICITLY present in
their latest message below. Do not guess or invent anything.

Fields to look for (use these exact keys):
- name
- location (village/town/district)
- education (educational background)
- family_occupation (their family's traditional work)
- current_livelihood (what they currently do for work)
- skills_interest (skills they have or want to learn)
- mobility (travel/physical constraints)
- employment_preference (self-employment vs. working for someone else)

Already known about this person: {json.dumps(profile)}

Their latest message: "{transcript}"

Return ONLY a JSON object containing keys for fields you found NEW
information for in this message. Omit any key you're not confident
about -- do not include null values, just leave the key out entirely.
"""
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": "You extract structured facts from natural conversation. Return only valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=300,
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.replace("```json", "").replace("```", "").strip()
        extracted = json.loads(raw)

        updated_profile = dict(profile)
        for field_key, value in extracted.items():
            if field_key in REQUIRED_FIELDS and value:
                updated_profile[field_key] = value
        return updated_profile

    except Exception as e:
        print(f"LLM extraction failed ({e}), falling back to single-field capture.")
        # FALLBACK: same behaviour as before this fix -- save the raw
        # transcript to whichever field is currently "next" in the fixed
        # order. This guarantees the conversation can never get stuck
        # just because the LLM call had a bad moment.
        missing = get_missing_fields(profile)
        if missing:
            updated_profile = dict(profile)
            updated_profile[missing[0]] = transcript
            return updated_profile
        return profile



def generate_natural_question(profile: dict, missing_fields: list) -> str:
    """
    Generates a warm, contextual next question -- referencing what's
    already known where it makes sense -- instead of reading a fixed
    script line. Falls back to the plain static question text if the
    LLM call fails, so this can never break the conversation.
    """
    next_field = missing_fields[0]
    fallback_question = dict(PROFILE_STEPS)[next_field]

    try:
        known_summary = ", ".join(f"{FIELD_LABELS[k]}: {v}" for k, v in profile.items() if v)
        prompt = f"""You are a warm, empathetic assistant helping a
government scheme beneficiary describe their background so you can
recommend suitable skill training. Do not sound administrative or
like a form.

What you already know about them: {known_summary or "nothing yet"}

You still need to find out about: {FIELD_LABELS[next_field]}

Write ONE short, natural, friendly question (1 sentence) to ask them
this next, in plain English. Do not greet them again if you already
know their name. Do not explain why you're asking.
"""
        response = client.chat.completions.create(
            model="qwen/qwen3.8-27b",
            messages=[
                {"role": "system", "content": "You write short, warm, natural conversational questions. Return only the question text, nothing else."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=60,
        )
        question = response.choices[0].message.content.strip().strip('"')
        return question if question else fallback_question
    except Exception as e:
        print(f"Natural question generation failed ({e}), falling back to fixed question.")
        return fallback_question



def build_profile_summary(profile: dict) -> str:
    """Human-readable summary shown/spoken back for confirmation."""
    lines = ["Here is what I understood about you:"]
    for field_key, _ in PROFILE_STEPS:
        value = profile.get(field_key, "-")
        lines.append(f"{FIELD_LABELS[field_key]}: {value}")
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