import os
import base64
import requests
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()
# ---- Config (fill these into a .env file, see .env.example) ----
SARVAM_API_KEY = os.environ["SARVAM_API_KEY"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
# This must be your ngrok https URL, e.g. https://abcd1234.ngrok-free.app
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"]

app = Flask(__name__)
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)


# ---------------------------------------------------------------------
# STEP 1: Twilio webhook -- this is the entry point for every message
# ---------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    num_media = int(request.form.get("NumMedia", 0))
    from_number = request.form.get("From")  # e.g. 'whatsapp:+91XXXXXXXXXX'

    resp = MessagingResponse()

    if num_media == 0:
        # Text message, not a voice note -- handle simply for now
        resp.message("Please send a voice note describing your work and skills 🎙️")
        return str(resp)

    media_url = request.form.get("MediaUrl0")
    content_type = request.form.get("MediaContentType0")
    print(f"Received {content_type} from {from_number}: {media_url}")

    # --- Download the incoming voice note from Twilio ---
    local_input_path = os.path.join(AUDIO_DIR, "incoming.ogg")
    download_twilio_media(media_url, local_input_path)

    # --- Convert to a format Sarvam accepts reliably (wav, 16kHz mono) ---
    wav_path = os.path.join(AUDIO_DIR, "incoming.wav")
    convert_to_wav(local_input_path, wav_path)

    # --- STEP 2: Speech to text ---
    transcript, detected_lang = sarvam_speech_to_text(wav_path)
    print(f"Transcript ({detected_lang}): {transcript}")

    # --- STEP 3: hand off to teammate's logic (NLU + recommendation) ---
    reply_text = get_recommendation_reply(transcript, from_number, detected_lang)

    # --- STEP 4: text to speech ---
    reply_audio_filename = "reply.wav"
    reply_audio_path = os.path.join(AUDIO_DIR, reply_audio_filename)
    sarvam_text_to_speech(reply_text, detected_lang, reply_audio_path)

    # --- STEP 5: reply on WhatsApp with the voice note ---
    reply_audio_public_url = f"{PUBLIC_BASE_URL}/audio/{reply_audio_filename}"
    msg = resp.message(reply_text)  # text fallback, shown alongside voice note
    msg.media(reply_audio_public_url)

    return str(resp)


# ---------------------------------------------------------------------
# Serves generated audio files so Twilio can fetch and send them
# ---------------------------------------------------------------------
@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)


# ---------------------------------------------------------------------
# Helper: download the voice note Twilio tells us about
# Twilio media URLs require your account SID + auth token as basic auth
# ---------------------------------------------------------------------
def download_twilio_media(media_url: str, save_path: str):
    response = requests.get(
        media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    )
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)


# ---------------------------------------------------------------------
# Helper: WhatsApp voice notes come in as .ogg (opus) -- convert to wav
# ---------------------------------------------------------------------
def convert_to_wav(input_path: str, output_path: str):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path, format="wav")


# ---------------------------------------------------------------------
# Sarvam Speech-to-Text (Saaras v3) -- REST API, good for clips < 30s
# ---------------------------------------------------------------------
def sarvam_speech_to_text(wav_path: str):
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}
    with open(wav_path, "rb") as f:
        files = {"file": (os.path.basename(wav_path), f, "audio/wav")}
        data = {"model": "saaras:v3"}  # auto-detects language across Indian langs
        response = requests.post(url, headers=headers, files=files, data=data)
    response.raise_for_status()
    result = response.json()
    return result["transcript"], result.get("language_code", "hi-IN")


# ---------------------------------------------------------------------
# Sarvam Text-to-Speech (Bulbul) -- takes text, returns base64 audio
# ---------------------------------------------------------------------
def sarvam_text_to_speech(text: str, language_code: str, save_path: str):
    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": SARVAM_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": [text],
        "target_language_code": language_code,
        "speaker": "meera",
        "model": "bulbul:v2",
        "speech_sample_rate": 16000,
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    audio_base64 = response.json()["audios"][0]
    with open(save_path, "wb") as f:
        f.write(base64.b64decode(audio_base64))


# ---------------------------------------------------------------------
# *** HANDOFF POINT TO PERSON 2 (NLU + Recommendation) ***
# Replace this stub with a call to their module once it's ready.
# Contract: takes a transcript + phone number + language, returns reply text.
# ---------------------------------------------------------------------
def get_recommendation_reply(transcript: str, from_number: str, language_code: str) -> str:
    """
    STUB -- replace with Person 2's actual pipeline, e.g.:

        from nlu_engine import extract_profile
        from recommender import get_top_matches

        profile = extract_profile(transcript)
        matches = get_top_matches(profile)
        return format_reply(matches, language_code)

    For now this just echoes back so you can test the voice loop end-to-end
    before the recommendation engine exists.
    """
    return f"I heard you say: {transcript}. Recommendations coming soon!"


if __name__ == "__main__":
    app.run(port=5000, debug=True)