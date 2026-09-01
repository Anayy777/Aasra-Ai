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

    resp = MessagingResponse()

    