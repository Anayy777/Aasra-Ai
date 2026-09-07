import os
import sys
import threading    
import base64
import requests
from pathlib import Path
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from pydub import AudioSegment
from dotenv import load_dotenv
import conversation as convo
from twilio.rest import Client

load_dotenv()

# Add recommendation-service to path

RECOMMENDATION_SERVICE_DIR = Path(__file__).resolve().parent.parent / "recommendation-service" / "app"
if str(RECOMMENDATION_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(RECOMMENDATION_SERVICE_DIR))
 
from app.recommender import recommend_from_profile
from app.normalizer import normalize_profile
from profile_adapter import build_beneficiary_profile



SARVAM_API_KEY = os.environ["SARVAM_API_KEY"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]

PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"]

twilio_client = Client(TWILIO_ACCOUNT_SID , TWILIO_AUTH_TOKEN)

app = Flask(__name__)
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)

@app.route("/webhook"  , methods=["POST"])
def whatsapp_webhook():
    from_number = request.form.get("From", "")
    to_number = request.form.get("To", "")
    num_media = int(request.form.get("NumMedia", 0))
    media_url = request.form.get("MediaUrl0", "")
    text_body = request.form.get("Body", "")

    # Fire background processing so Twilio receives an instant 200 response
    thread = threading.Thread(
        target=process_message_async,
        args=(from_number, to_number, num_media, media_url, text_body)
    )
    thread.start()

    # Instant empty response to satisfy Twilio's 15s window
    return "", 200
    
    # Send one bot reply as BOTH voice note (in the user's language) and English text (always English, per the design decision).

def send_whatsapp_reply(to_number: str, from_number: str, text: str, audio_public_url: str):
    # 1. Send the text message first
    twilio_client.messages.create(
        body=text,
        from_=from_number,
        to=to_number
    )

    # 2. Send the voice note as a separate media message
    twilio_client.messages.create(
        from_=from_number,
        to=to_number,
        media_url=[audio_public_url]
    )




# Pre generated audio files to Sarvam by server to user

@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR , filename)

# Helper Functions : 

# TO DETECT USER LANGUAGE

def detect_text_language(text: str) -> str:
    for ch in text:
        if "\u0900" <= ch <= "\u097F":  # Devanagari block
            return "hi-IN"
    return "en-IN"

# translate english prompt to user lang before feeding to TTS model 

def translate_for_speech(text: str, target_language_code: str) -> str:
    if target_language_code.startswith("en"):
        return text
    try:
        url = "https://api.sarvam.ai/translate"
        headers = {
            "api-subscription-key": SARVAM_API_KEY,
            "Content-Type": "application/json",
        }
        payload = {
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": target_language_code,
        }
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["translated_text"]
    except Exception as e:
        print(f"Translation failed ({e}), falling back to English text for speech.")
        return text
 
 
def sanitize(phone_number: str) -> str:
    """Turns 'whatsapp:+919876543210' into a filename-safe string."""
    return phone_number.replace("whatsapp:", "").replace("+", "")
 


# DOWNLOAD TWILIO VOICE-NOTES

def download_twilio_media(media_url : str , save_path : str):
    response = requests.get(
        media_url , auth = (TWILIO_ACCOUNT_SID , TWILIO_AUTH_TOKEN)
    )
    response.raise_for_status()
    with open(save_path , "wb") as f:
        f.write(response.content)


# VOICE NOTES COMES AS .ogg , CONVERT THEM TO wav

def convert_to_wav(input_path : str , output_path :str):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path , format = "wav")

# CONVERT WAV TO WHATSAPP SUPPORTED FORMAT (MP3)

def wav_to_mp3(input_path : str , output_path : str):
    audio = AudioSegment.from_wav(input_path)
    audio.export(output_path , format = "mp3")



# SARVAM SPEECH TO TEXT (< 30 SECS FOR NOW)

def sarvam_speech_to_text(wav_path: str):
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key" : SARVAM_API_KEY}
    with open(wav_path , "rb") as f:
        files = {"file" : (os.path.basename(wav_path) , f , "audio/wav")}
        data  = {"model" : "saaras:v3"} # detects language across india

        response = requests.post(url , headers = headers , files = files , data = data)
    response.raise_for_status()
    result = response.json()
    return result["transcript"] , result.get("language_code" ,"hi-IN")
# SARVAM TEXT TO SPEECH-- BULBUL  

    
def sarvam_text_to_speech(text: str, language_code: str, save_path: str):
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": [text],
        "target_language_code": language_code,
        "speaker": "ritu",
        "model": "bulbul:v3",
        "speech_sample_rate": 16000,
    }
    response = requests.post(url, headers=headers, json=payload)
    if not response.ok:
        print("Sarvam error : " , response.text)
    response.raise_for_status()
    audio_base64 = response.json()["audios"][0]
    with open(save_path, "wb") as f:
        f.write(base64.b64decode(audio_base64))

# RECOMMENDATION AND NLU PART , TAKE TRANSCRIPT , phone no and language and return reply text

def get_recommendation_reply(profile : dict, language_code: str) -> str:
    name = profile.get("name", "there")
 
    beneficiary_profile = build_beneficiary_profile(profile)
    beneficiary_profile = normalize_profile(beneficiary_profile)
 
    result = recommend_from_profile(
        profile=beneficiary_profile,
        user_latitude=None,
        user_longitude=None,
        top_k=3,
        language_code="en-IN",
    )
 
    return f"Thanks {name}!\n{result['reply']}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)