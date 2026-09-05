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

