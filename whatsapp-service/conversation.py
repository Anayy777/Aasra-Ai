"""

Guided conversation state machine.
 
Each WhatsApp phone number gets its own "session" that tracks:
  - what language they're speaking (detected from their first message)
  - which profile question they're currently on
  - the answers collected so far

"""

PROFILE_STEPS = [
    ("name" , "what is your name?") , 
    ("location", "Which village, town or district do you live in?"),
    ("education", "What is your educational background?"),
    ("current_livelihood" , "What do you currently do for work , if anything?") , 
    ("skills_interest", "What skills do you have, or what would you like to learn?"), 
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
EDITING = "EDITING"
DONE = "DONE"


SESSION = {} # to store information

def getSession(phone_no : str):
  """
    returns the existing conversation for this number , otherwise None if its a new conversation
  """

  return SESSION.get(phone_no)

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
  SESSION[phone_no] = session
  return session


def resetSession(phone_no : str):
  SESSION.pop(phone_no , None)


def curerntQuestion(session) -> str : 

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
                  "field you want to change, e.g. 'edit location'.)")
  return "\n".join(lines)


  