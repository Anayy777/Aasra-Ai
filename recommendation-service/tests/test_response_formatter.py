from app.response_formatter import format_recommendation_reply


result = {
    "recommendations": [
        {
            "course_id": "C001",
            "course_name": "Electrician",
            "skill_score": 0.8177583245211001,
            "location_score": 1.0,
            "distance_km": 0,
            "final_score": 0.87243082716477
        },
        {
            "course_id": "C003",
            "course_name": "CCTV Installation Technician",
            "skill_score": 0.6569729210330906,
            "location_score": 0.7912481839991229,
            "distance_km": 2.087518160008771,
            "final_score": 0.6972554999229003
        },
        {
            "course_id": "C002",
            "course_name": "Solar PV Installer",
            "skill_score": 0.35630042933313816,
            "location_score": 0.9103850332192795,
            "distance_km": 0.8961496678072047,
            "final_score": 0.5225258104989805
        }
    ]
}


reply = format_recommendation_reply(result)

print(reply)