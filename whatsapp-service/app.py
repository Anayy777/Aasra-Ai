import os
import base64
import requests
from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from pydub import AudioSegment
from dotenv import load_dotenv

load_dotenv()

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



    if num_media == 0:
        resp.message("Please send a voice note describing your work and skills")
        return str(resp)

    media_url = request.form.get("MediaUrl0") # 
    content_type = request.form.get("MediaContentType0") # gets me the content type of the media file

    print(f"Received {content_type} from {from_number}: {media_url}")

    local_input_path = os.path.join(AUDIO_DIR , "incoming.ogg")

    download_twilio_media(media_url , local_input_path)

    # Convert to a format Sarvam accepts i.e the wav format

    wav_path = os.path.join(AUDIO_DIR , "incoming.wav")
    convert_to_wav(local_input_path , wav_path)

    transcript , detectedLanguage = sarvam_speech_to_text(wav_path) #  the audion is the input in sarvam supported format
    print(f"Tranascript ({detectedLanguage}) : {transcript}")

    # Reccomendation logic part
    reply_text = get_recommendation_reply(transcript , from_number , detected_lang)

    # Convert the reccomendation text to audio

    reply_audio_filename = "reply.wav"
    reply_audio_path = os.path.join(AUDIO_DIR , reply_audio_filename)

    sarvam_text_to_speech(reply_text , detected_lang , reply_audio_path)

    # Reply on WhatsApp with the voice note

    reply_audio_public_url = f"{PUBLIC_BASE_URL}/audio/{reply_audio_filename}"

    msg = resp.message(reply_text)

    msg.media(reply_audio_public_url)

    return str(resp)



    # Pre generated audio files to Sarvam by server to user

    @app.route("/audio/<filename>")
    def serve_audio(filename):
        return send_from_directory(AUDIO_DIR , filename)

    # Helper Functions : 

    # DOWNLOAD TWILIO VOICE-NOTES

    def download_twilio_media(media_url : str , save_path : str):
        response = requests.get(
            media_url , auth = (TWILIO_ACCOUNT_SID , TWILIO_AUTH_TOKEN)
        )
        response.raise_for_status()
        with open(save_path , "wb") as f:
            f.write(response.content)


    # VOICE NOTES COMES AS .ogg , CONVERT THEM TO wav

    def convert_to_wav:
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frme_rate(16000).set_channels[1]
        audio.export(output_path , format = "wav")


