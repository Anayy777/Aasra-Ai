import traceback
import os
import sys
import base64
import requests
from pathlib import Path
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from pydub import AudioSegment
from dotenv import load_dotenv

import conversation as convo

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "recommendation-service"))

from app.recommender import recommend_from_profile
from app.normalizer import normalize_profile
from profile_adapter import build_beneficiary_profile

SARVAM_API_KEY = os.environ["SARVAM_API_KEY"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
PUBLIC_BASE_URL = os.environ["PUBLIC_BASE_URL"]

app = Flask(__name__)
AUDIO_DIR = "audio_files"
os.makedirs(AUDIO_DIR, exist_ok=True)



# Main webhook -- entry point for every incoming WhatsApp message

@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    from_number = request.form.get("From")
    num_media = int(request.form.get("NumMedia", 0))

    resp = MessagingResponse()

    # Step 1: get transcript + language, from voice or text
    if num_media > 0:
        media_url = request.form.get("MediaUrl0")
        local_input_path = os.path.join(AUDIO_DIR, f"incoming_{sanitize(from_number)}.ogg")
        download_twilio_media(media_url, local_input_path)

        wav_path = os.path.join(AUDIO_DIR, f"incoming_{sanitize(from_number)}.wav")
        convert_to_wav(local_input_path, wav_path)

        transcript, detected_lang = sarvam_speech_to_text(wav_path)
    else:
        transcript = request.form.get("Body", "").strip()
        detected_lang = detect_text_language(transcript)

    print(f"[{from_number}] ({detected_lang}) said: {transcript}")

    # Step 2: run the conversation state machine
    session = convo.get_session(from_number)

    if session is None:
        # Brand new user - greet them and ask the first question
        session = convo.create_session(from_number, detected_lang)
        greeting = "Hello! I'm here to help you find training and work opportunities that suit you."
        question = convo.current_question(session)
        reply_text = f"{greeting} {question}"
        send_reply(resp, reply_text, session["language"])
        return str(resp)

    if session["state"] == convo.COLLECTING:
        field_key = convo.current_field(session)
        session["profile"][field_key] = transcript

        if convo.is_last_step(session):
            session["state"] = convo.CONFIRMING
            reply_text = convo.build_profile_summary(session["profile"])
        else:
            convo.advance_step(session)
            reply_text = convo.current_question(session)

        convo.save_session(from_number, session)  # persist the mutation above
        send_reply(resp, reply_text, session["language"])
        return str(resp)

    if session["state"] == convo.CONFIRMING:
        if convo.is_confirmation(transcript):
            session["state"] = convo.DONE
            convo.save_session(from_number, session)
            # *** HANDOFF POINT TO PERSON 2 ***
            full_text, voice_summary = get_recommendation_reply(session["profile"], session["language"])
            send_reply(resp, full_text, session["language"], voice_text=voice_summary)
            return str(resp)

        edit_field = convo.match_edit_field(transcript)
        if edit_field:
            session["state"] = convo.EDITING_SINGLE
            session["editing_field"] = edit_field
            convo.save_session(from_number, session)
            question = dict(convo.PROFILE_STEPS)[edit_field]
            send_reply(resp, question, session["language"])
            return str(resp)

        # Didn't understand -- re-show the summary/instructions
        reply_text = convo.build_profile_summary(session["profile"])
        send_reply(resp, reply_text, session["language"])
        return str(resp)

    if session["state"] == convo.EDITING_SINGLE:
        field_key = session["editing_field"]
        session["profile"][field_key] = transcript
        session["state"] = convo.CONFIRMING
        session["editing_field"] = None
        convo.save_session(from_number, session)
        reply_text = convo.build_profile_summary(session["profile"])
        send_reply(resp, reply_text, session["language"])
        return str(resp)

    if session["state"] == convo.DONE:
        if "restart" in transcript.lower():
            convo.reset_session(from_number)
            new_session = convo.create_session(from_number, detected_lang)
            reply_text = "Sure, let's start over. " + convo.PROFILE_STEPS[0][1]
            send_reply(resp, reply_text, new_session["language"])
        else:
            reply_text = "Your profile is already complete. Say 'restart' if you'd like to build a new one."
            send_reply(resp, reply_text, session["language"])
        return str(resp)

    return str(resp)

    # The heavy conversation state logic


#------------------------------------------------------------------
# Sends one bot reply as BOTH voice note (in the user's language) and
# English text (always English, per the design decision).

def send_reply(resp: MessagingResponse, english_text: str, language_code: str, voice_text: str = None):
    """
    english_text: what's shown in the WhatsApp text message (can be long/detailed)
    voice_text: shorter version . If not given,
    english_text is used for speech too --,
    since Sarvam's TTS rejects any input over 500 characters, and a
    500-char cutoff mid-sentence sounds broken. Whichever text
    is actually used, this always keeps the pipeline from crashing.
    """
    text_for_speech = voice_text if voice_text is not None else english_text
    speech_text = translate_for_speech(text_for_speech, language_code)
    speech_text = truncate_for_tts(speech_text)

    reply_wav_path = os.path.join(AUDIO_DIR, "reply.wav")
    sarvam_text_to_speech(speech_text, language_code, reply_wav_path)

    reply_audio_filename = "reply.mp3"
    reply_audio_path = os.path.join(AUDIO_DIR, reply_audio_filename)
    convert_wav_to_mp3(reply_wav_path, reply_audio_path)

    reply_audio_public_url = f"{PUBLIC_BASE_URL}/audio/{reply_audio_filename}"

    # FIXED: WhatsApp does not render captions on audio-type media -- a

    # drops the text and only delivers the voice note. Sending two

    resp.message(english_text)          # text message
    audio_msg = resp.message()          # separate voice-note message
    audio_msg.media(reply_audio_public_url)


@app.route("/audio/<filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)



# Helper Function to detect text language

def detect_text_language(text: str) -> str:
    for ch in text:
        if "\u0900" <= ch <= "\u097F":  # Devanagari block
            return "hi-IN"
    return "en-IN"



# Helper: Sarvam's TTS API rejects any input over 500 characters. This
# is a last-resort safety net -- cuts at the last full sentence under
# the limit where possible, so it doesn't chop off mid-word.

def truncate_for_tts(text: str, max_len: int = 480) -> str:
    if len(text) <= max_len:
        return text
    truncated = text[:max_len]
    last_period = truncated.rfind(".")
    if last_period > 100:  # only cut at a sentence boundary if it's not too early
        return truncated[:last_period + 1]
    return truncated.rstrip() + "..."


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



# Twilio media download

def download_twilio_media(media_url: str, save_path: str):
    response = requests.get(media_url, auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN))
    response.raise_for_status()
    with open(save_path, "wb") as f:
        f.write(response.content)


def convert_to_wav(input_path: str, output_path: str):
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_frame_rate(16000).set_channels(1)
    audio.export(output_path, format="wav")


def convert_wav_to_mp3(input_path: str, output_path: str):
    audio = AudioSegment.from_wav(input_path)
    audio.export(output_path, format="mp3")


def sarvam_speech_to_text(wav_path: str):
    url = "https://api.sarvam.ai/speech-to-text"
    headers = {"api-subscription-key": SARVAM_API_KEY}
    with open(wav_path, "rb") as f:
        files = {"file": (os.path.basename(wav_path), f, "audio/wav")}
        data = {"model": "saaras:v3"}
        response = requests.post(url, headers=headers, files=files, data=data, timeout=10)
    if not response.ok:
        print("Sarvam STT error:", response.text)
    response.raise_for_status()
    result = response.json()
    return result["transcript"], result.get("language_code", "hi-IN")


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
    response = requests.post(url, headers=headers, json=payload, timeout=10)
    if not response.ok:
        print("Sarvam TTS error:", response.text)
    response.raise_for_status()
    audio_base64 = response.json()["audios"][0]
    with open(save_path, "wb") as f:
        f.write(base64.b64decode(audio_base64))



# Recommendation engine hookup -- runs once the guided conversation is
# confirmed complete. Converts our raw profile dict into the structured
# schema the recommender expects, geocodes the stated location into
# coordinates, then ranks courses and formats a reply.

def get_recommendation_reply(profile: dict, language_code: str):

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

    full_text = f"Thanks {name}!\n{result['reply']}"

    recommendations = result.get("recommendations", [])
    if recommendations:
        top = recommendations[0]
        title = top.get("qualification_title", "a suitable qualification")
        voice_summary = (
            f"Thanks {name}! Your top recommendation is {title}, "
            f"with a {top.get('final_score', 0) * 100:.0f} percent match. "
            f"I've sent the full list with {len(recommendations)} options as a text message."
        )
    else:
        voice_summary = f"Thanks {name}! I couldn't find a strong match right now -- check the text message for details."

    return full_text, voice_summary


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=5001, debug=False)