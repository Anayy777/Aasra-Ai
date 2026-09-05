from app.recommender import recommend_from_transcript


transcript = """
Main 12th pass hoon. Main Delhi mein rehta hoon.
Maine electrician ka kaam kiya hai aur electrical wiring
aur maintenance ka experience hai. Mujhe full time job chahiye.
Main maximum 10 kilometer tak travel kar sakta hoon.
"""


result = recommend_from_transcript(
    transcript=transcript,
    user_latitude=28.6139,
    user_longitude=77.2090,
    top_k=3
)


print("\nPROFILE")
print(result["profile"])


print("\nRECOMMENDATIONS")

for recommendation in result["recommendations"]:
    print(
        recommendation["course_id"],
        recommendation["course_name"],
        "| Skill:",
        round(recommendation["skill_score"], 3),
        "| Location:",
        round(recommendation["location_score"], 3),
        "| Distance:",
        round(recommendation["distance_km"], 2),
        "km",
        "| Final:",
        round(recommendation["final_score"], 3)
    )

print("\nREPLY")

print(result["reply"])

print("\nEMPTY TRANSCRIPT TEST")

empty_result = recommend_from_transcript(
    transcript="",
    user_latitude=28.6139,
    user_longitude=77.2090,
    top_k=3
)

print(empty_result)

print("\nTOP K TEST")

top_k_result = recommend_from_transcript(
    transcript=transcript,
    user_latitude=28.6139,
    user_longitude=77.2090,
    top_k=1
)

print("Number of recommendations:", len(top_k_result["recommendations"]))

for recommendation in top_k_result["recommendations"]:
    print(
        recommendation["course_id"],
        recommendation["course_name"]
    )

print("\nNO ELIGIBLE COURSE TEST")

no_match_transcript = """
Main 12th pass hoon.
Main Delhi mein rehta hoon.
Mujhe part time job chahiye.
Main maximum 1 kilometer tak travel kar sakta hoon.
"""

no_match_result = recommend_from_transcript(
    transcript=no_match_transcript,
    user_latitude=28.6139,
    user_longitude=77.2090,
    top_k=3
)

print("Recommendations:", no_match_result["recommendations"])
print("Reply:", no_match_result["reply"])
print("Number of recommendations:", len(top_k_result["recommendations"]))
assert len(top_k_result["recommendations"]) == 1
print(empty_result)
assert empty_result["profile"] is None
assert empty_result["recommendations"] == []