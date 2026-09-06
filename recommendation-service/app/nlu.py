import os
import json

from dotenv import load_dotenv
from groq import Groq

from app.models import BeneficiaryProfile


load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def extract_profile(
    transcript: str,
    language_code: str | None = None
) -> BeneficiaryProfile:

    prompt = f"""
You are an information extraction system for a government skilling
recommendation platform.

Extract the beneficiary's information from the transcript below.

Return ONLY valid JSON.

The JSON must contain exactly these fields:
- education
- occupation
- skills
- location
- mobility
- employment_preference

Rules:
1. Do not invent information.
2. If information is not provided, use null.
3. skills must be a list of strings.
4. mobility must contain max_distance_km.
5. If maximum travel distance is not mentioned, max_distance_km must be null.
6. Keep the values concise and normalized.
7. Understand Hindi, Hinglish and English.
8. language_code must be the language code provided by the speech recognition system.
9. Do not detect or guess the language yourself.

Transcript:
{transcript}
Language code:
{language_code}
"""

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {
                "role": "system",
                "content": "You extract structured information from beneficiary conversations."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=500
    )

    raw_output = response.choices[0].message.content.strip()

    # Remove markdown code fences if the model returns them
    if raw_output.startswith("```"):
        raw_output = raw_output.replace("```json", "")
        raw_output = raw_output.replace("```", "")
        raw_output = raw_output.strip()

    try:
        data = json.loads(raw_output)

    except json.JSONDecodeError as error:
        raise ValueError(
            f"Qwen returned invalid JSON:\n{raw_output}"
        ) from error

    profile = BeneficiaryProfile.model_validate(data)
    profile.language_code = language_code

    return profile

def update_profile_from_answer(
    profile: BeneficiaryProfile,
    answer: str
) -> BeneficiaryProfile:

    prompt = f"""
You are updating an existing beneficiary profile for a
government skilling recommendation platform.

Existing profile:
{profile.model_dump_json()}

The beneficiary has now given this answer:

{answer}

Update the existing profile using ONLY information present
in the new answer.

Rules:
1. Do not remove existing information.
2. Do not invent information.
3. Update only fields supported by the answer.
4. Keep existing values when the answer does not provide new information.
5. skills must remain a list of strings.
6. mobility must contain max_distance_km.
7. If the answer does not mention mobility, keep the existing mobility value.
8. Understand Hindi, Hinglish and English.
9. Return ONLY valid JSON.

Return exactly these fields:
- education
- occupation
- skills
- location
- mobility
- employment_preference
- language_code
"""

    response = client.chat.completions.create(
        model="qwen/qwen3.8-27b",
        messages=[
            {
                "role": "system",
                "content": (
                    "You update structured beneficiary profiles "
                    "from conversational answers."
                )
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=500
    )

    raw_output = response.choices[0].message.content.strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.replace("```json", "")
        raw_output = raw_output.replace("```", "")
        raw_output = raw_output.strip()

    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"Qwen returned invalid JSON:\n{raw_output}"
        ) from error

    updated_profile = BeneficiaryProfile.model_validate(data)

    return updated_profile