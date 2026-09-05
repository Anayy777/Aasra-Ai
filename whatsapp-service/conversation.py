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