from app.nlu import extract_profile


transcript = """
Main 12th pass hoon. Main Delhi mein rehta hoon.
Maine electrician ka kaam kiya hai aur electrical wiring
aur maintenance ka experience hai. Mujhe full time job chahiye.
Main maximum 10 kilometer tak travel kar sakta hoon.
"""


profile = extract_profile(transcript)

print(profile.model_dump())

print("\nHINGLISH TEST")

hinglish_transcript = """
Main barahvi pass hoon aur Delhi mein rehta hoon.
Main bijli ka kaam karta hoon.
Mujhe wiring aur maintenance aata hai.
Mujhe full time kaam chahiye.
Main 10 kilometer tak travel kar sakta hoon.
"""

hinglish_profile = extract_profile(hinglish_transcript)

print(hinglish_profile.model_dump())