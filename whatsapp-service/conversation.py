"""
Guided conversation state machine.
 
Each WhatsApp phone number gets its own "session" that tracks:
  - what language they're speaking (detected from their first message)
  - which profile question they're currently on
  - the answers collected so far

"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, delete, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, SessionLocal
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
# If the user wants to edit anything in their profile card , some reference aliases for each field 


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

# SESSION STATES

COLLECTING = "COLLECTING"
CONFIRMING  = "CONFIRMING"
EDITING_SINGLE = "EDITING_SINGLE"
DONE = "DONE"



class ConversationSession(Base):
  __tablename__ = "conversation_sessions"

  phone_number: Mapped[str] = mapped_column(String(32), primary_key=True)
  language: Mapped[str] = mapped_column(String(16), nullable=False)
  state: Mapped[str] = mapped_column(String(32), nullable=False)
  step_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  profile: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
  editing_field: Mapped[str | None] = mapped_column(String(64), nullable=True)
  created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True), nullable=False, server_default=func.now()
  )
  updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    nullable=False,
    server_default=func.now(),
    onupdate=func.now(),
  )


def _session_dict(record: ConversationSession) -> dict:
  return {
    "language": record.language,
    "state": record.state,
    "step_index": record.step_index,
    "profile": record.profile or {},
    "editing_field": record.editing_field,
  }

def getSession(phone_no : str):
  """
    returns the existing conversation for this number , otherwise None if its a new conversation
  """

  with SessionLocal() as db:
    record = db.get(ConversationSession, phone_no)
    return _session_dict(record) if record else None

def createSession(phone_no : str , language_code : str):
  """
    Start a fresh session
  """
  session = {
    "language": language_code,
    "state": COLLECTING,
    "step_index": 0,
    "profile": {},
    "editing_field": None,
  }
  with SessionLocal() as db:
    record = db.get(ConversationSession, phone_no)
    if record is None:
      record = ConversationSession(phone_number=phone_no)
      db.add(record)

    record.language = language_code
    record.state = COLLECTING
    record.step_index = 0
    record.profile = {}
    record.editing_field = None
    db.commit()
    db.refresh(record)
    return _session_dict(record)


def resetSession(phone_no : str):
  with SessionLocal() as db:
    db.execute(
        delete(ConversationSession).where(
            ConversationSession.phone_number == phone_no
        )
    )
    db.commit()


def saveSession(phone_no: str, session: dict):
  """Persist changes made to an existing session dictionary."""
  with SessionLocal() as db:
    record = db.get(ConversationSession, phone_no)
    if record is None:
      record = ConversationSession(phone_number=phone_no)
      db.add(record)

    record.language = session["language"]
    record.state = session["state"]
    record.step_index = session["step_index"]
    record.profile = dict(session["profile"])
    record.editing_field = session["editing_field"]
    db.commit()
    db.refresh(record)
    return _session_dict(record)


def currentQuestion(session) -> str : 

  field_key , question = PROFILE_STEPS[session["step_index"]]
  return question




def currentField(session) -> str:

  field_key, _ = PROFILE_STEPS[session["step_index"]]
  return field_key


def is_last_step(session) -> bool:
  return session["step_index"] >= len(PROFILE_STEPS) - 1


def advance_step(session):
  session["step_index"] += 1

def profile_summary(profile : dict) -> str:
   """Human-readable summary shown/spoken back for confirmation."""

   lines = ["Here is what is understood about you : "]
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

   for field_key , _ in PROFILE_STEPS:
      value = profile.get(field_key , "-")
      lines.append(f"{labels[field_key]} : {value}")
   lines.append("Reply 'confirm' if this is correct, or say 'edit' and the "
                  "field you want to change, e.g. 'edit location'.")
   return "\n".join(lines)

def edit_profile(text: str):
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
 