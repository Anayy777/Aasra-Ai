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

@app.route("/webhook"  , methods=["POST"])
def whatsapp_webhook():
    num_media = int(request.form.get("NumMedia" , 0)) # gets me the number of media files in the message
    from_number = request.form.get("From") # gets me the phone number of the sender

    resp = MessagingResponse() #



    if num_media > 0:
        media_url = request.form.get("MediaUrl0")
        local_input_path = os.path.join(AUDIO_DIR, f"incoming_{sanitize(from_number)}.ogg")
        download_twilio_media(media_url, local_input_path)
 
        wav_path = os.path.join(AUDIO_DIR, f"incoming_{sanitize(from_number)}.wav")
        convert_to_wav(local_input_path, wav_path)
 
        transcript, detectedLanguage = sarvam_speech_to_text(wav_path)
    else:
        transcript = request.form.get("Body", "").strip()
        detectedLanguage = detect_text_language(transcript)
    print(f"Tranascript ({detectedLanguage}) : {transcript}")

    # CONVERSATION STATE

    session = convo.getSession(from_number)

    if session is None:
        session = convo.createSession(from_number , detectedLanguage)

        greeting = "Hello! I'm here to help you find training and work opportunities that suit you."

        question =convo.currentQuestion(session)
        reply_text = f"{greeting} {question}"

        send_reply(resp , reply_text , session["language"])
        return str(resp)
    # set state
    if(session['state'] == convo.COLLECTING):
        field_key = convo.currentField(session)
        session["profile"][field_key] = transcript

        if(convo.is_last_step(session)):
            session["state"] = convo.CONFIRMING
            reply_text = convo.profile_summary(session["profile"])

        else:
            convo.advance_step(session)
            reply_text = convo.currentQuestion(session)
        
        send_reply(resp , reply_text , session["language"])
        return str(resp)


    if(session['state'] == convo.CONFIRMING):
        if convo.is_confirmation(transcript):
            session["state"] = convo.DONE
            reply_text = get_recommendation_reply(session["profile"], session["language"])
            send_reply(resp, reply_text, session["language"])
            return str(resp)

        edit_field = convo.edit_profile(transcript)
        if edit_field: # if it exists
            session["state"] = convo.EDITING_SINGLE
            session["editing_field"] = edit_field
            question = dict(convo.PROFILE_STEPS)[edit_field]

            send_reply(resp , question , session["language"])
            return str(resp)

        reply_text = convo.profile_summary(session["profile"])
        send_reply(resp, reply_text, session["language"])
        return str(resp)
    
    if session["state"] == convo.EDITING_SINGLE:
        field_key = session["editing_field"]
        session["profile"][field_key] = transcript
        session["state"] = convo.CONFIRMING
        session["editing_field"] = None
        reply_text = convo.profile_summary(session["profile"])
        send_reply(resp , reply_text , session["language"])
        return str(resp)

    if session["state"] == convo.DONE:
        if "RESTART" in transcript.lower():
            convo.resetSession(from_number)
            new_session = convo.createSession(from_number , detectedLanguage)
            reply_text = "Sure , let's start over. " + convo.PROFILE_STEPS[0][1]
            send_reply(resp , reply_text , new_session["language"])
        else:
            reply_text = "Your profile is already complete. Say 'restart' if you'd like to build a new one."
            send_reply(resp , reply_text , session["language"])
        return str(resp)

    return str(resp)
    
    # Send one bot reply as BOTH voice note (in the user's language) and English text (always English, per the design decision).

    # Convert the reccomendation text to audio
def send_reply(resp: MessagingResponse, english_text: str, language_code: str):

    speech_text = translate_for_speech(english_text , language_code)
    reply_wav_path = os.path.join(AUDIO_DIR, "reply.wav")
    sarvam_text_to_speech(reply_text, language_code , reply_wav_path)

    reply_audio_filename = "reply.mp3"
    reply_audio_path = os.path.join(AUDIO_DIR, reply_audio_filename)
    wav_to_mp3(reply_wav_path, reply_audio_path)

    # Reply on WhatsApp with the voice note

    reply_audio_public_url = f"{PUBLIC_BASE_URL}/audio/{reply_audio_filename}"
    msg = resp.message(english_text)

    msg.media(reply_audio_public_url)




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