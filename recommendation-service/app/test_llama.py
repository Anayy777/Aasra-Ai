import os

from dotenv import load_dotenv
from groq import Groq

# Load variables from .env
load_dotenv()

# Get API key
api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY not found in .env file")

# Create Groq client
client = Groq(api_key=api_key)

# Send request to Qwen
response = client.chat.completions.create(
    model="qwen/qwen3.8-27b",
    messages=[
        {
            "role": "user",
            "content": "Explain what an electrician does in one sentence."
        }
    ]
)

# Print Qwen's response
print(response.choices[0].message.content)