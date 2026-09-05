from fastapi.testclient import TestClient

from app.api import app


client = TestClient(app)


print("\nHEALTH CHECK TEST")

response = client.get("/")

print("Status:", response.status_code)
print("Response:", response.json())

assert response.status_code == 200
assert response.json()["status"] == "running"

print("\nRECOMMEND ENDPOINT TEST")

request_data = {
    "transcript": """
    Main 12th pass hoon. Main Delhi mein rehta hoon.
    Maine electrician ka kaam kiya hai aur electrical wiring
    aur maintenance ka experience hai. Mujhe full time job chahiye.
    Main maximum 10 kilometer tak travel kar sakta hoon.
    """,
    "user_latitude": 28.6139,
    "user_longitude": 77.2090,
    "top_k": 3
}

response = client.post(
    "/recommend",
    json=request_data
)

print("Status:", response.status_code)
print("Response:", response.json())

assert response.status_code == 200

data = response.json()

assert "profile" in data
assert "recommendations" in data
assert "reply" in data

assert len(data["recommendations"]) == 3
