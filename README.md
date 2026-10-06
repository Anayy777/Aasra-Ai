# AASRA-AI

AASRA-AI helps people find skill training that fits the work they already know, what they want to learn, and their circumstances. Someone can send a voice note on WhatsApp, answer a few questions in their language, and get training suggestions back as audio and text.

The idea is straightforward. A person should be able to say “I do electrical repair work and want to learn more” and get help figuring out a useful next step, without working through a long online form.

**This is a working prototype.** The WhatsApp conversation, voice replies and qualification recommendations are connected. Linking every recommendation to a real provider with an available batch is still in progress.

## Try it on WhatsApp

The team needs to have the bot and its public tunnel running first.

1. Open the [Twilio WhatsApp Sandbox chat](https://wa.me/14155238886).
2. Send the join phrase shown in the team's Twilio Sandbox console. Our earlier demo used `join smooth-twelve`; check the console if that phrase no longer works.
3. Send `hi`, as text or a voice note.
4. Answer the bot's follow-up questions. It asks about your name, location, education, family occupation, current work, skills or interests, travel or physical constraints, and preference for self-employment or a job.
5. Check the profile summary and reply `yes` to confirm. To fix something, use a clear instruction such as `change location`, then send the corrected answer.
6. Read the top three qualification suggestions and listen to the short explanation. Related training-centre links appear when the catalogue has a match.

After receiving recommendations, send `restart` or `start over` to begin again.

## How it works

```text
WhatsApp text or voice note
          |
          v
Twilio -> Flask webhook
          |
          +-- Voice: download -> FFmpeg conversion -> Sarvam Saaras
          +-- Text: use the message directly
          |
          v
Groq / Qwen extracts profile details and asks for missing information
          |
          v
User confirms the profile
          |
          v
NQR matching and ranking -> training catalogue lookup
          |
          v
Text reply + Sarvam translation and Bulbul speech -> WhatsApp
```

Each phone number has a conversation session in SQLite, so answers survive server restarts. The detected language is updated on each message. Voice uses Sarvam's language detection; typed messages currently use a simple Hindi-script check and otherwise default to English.

The voice recommendation is shorter than the text reply, which carries the course details and links. Text replies are intended to be English, although the recommendation formatter still contains some Hindi/Hinglish wording.

The LLM turns the conversation into a structured profile. Python code then compares the person's occupation and skills with the NQR qualifications. Ranking uses **75% relevance and 25% specificity**, with additional handling for instructor qualifications. The displayed match percentage is a ranking score, not a chance of admission or employment.

The dataset does not contain a dedicated minimum-education requirement for every qualification, so admission eligibility cannot be fully verified. An NSQF level is not treated as a school-grade requirement.

## The data and training links

| File | What it is used for |
| --- | --- |
| [Aasra_NQR_Cleaned.xlsx](recommendation-service/data/Aasra_NQR_Cleaned.xlsx) | Qualification recommendations, using the `active_qualifications` sheet. |
| [training_offerings.csv](recommendation-service/data/training_offerings.csv) | Training-centre listings, source pages and admissions links. |
| [training_offerings.example.csv](recommendation-service/data/training_offerings.example.csv) | Column headings for adding catalogue records. |

The catalogue currently has **14 course listings across four Delhi government ITIs**, covering electrician, fitter, sewing, welder and plumber trades. They are related local options, not verified open batches for the exact recommended NQR qualifications. Similar trade names in the workbook include instructor qualifications, so these ITI learner courses deliberately have no exact NQR ID assigned.

Listings stop appearing after 30 days unless reviewed again. Without coordinates, a user's location must match the listed district or state. The WhatsApp flow currently supplies no coordinates, so distance from the user is unverified.

See [the training catalogue guide](recommendation-service/TRAINING_OFFERS.md) before adding providers. A listing needs a checked source; an open batch also needs its exact qualification and batch details. The bot does not log users into admissions portals, complete e-KYC or enroll them. Those steps happen through the relevant provider or scheme portal.

## Run the WhatsApp bot locally

You need Python **3.14** and `uv` for the root project, FFmpeg for audio conversion, Twilio Sandbox credentials, and Sarvam and Groq API keys. You also need a public HTTPS tunnel, such as ngrok, so Twilio can reach your local server.

From the repository root:

```bash
uv sync
```

Install FFmpeg if needed: `brew install ffmpeg` on macOS, or `sudo apt install ffmpeg` on Ubuntu/Debian.

Create a root `.env` using `.env.example` as a starting point. Edit an existing file instead of overwriting it. It needs:

```dotenv
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
SARVAM_API_KEY=your_sarvam_key
GROQ_API_KEY=your_groq_key
PUBLIC_BASE_URL=https://your-public-tunnel-host
```

Add `GROQ_API_KEY` manually; the root example currently omits it. The example's `TWILIO_PHONE_NUMBER` is not read by the current webhook, which replies through TwiML. Keep keys in `.env`, which is ignored by Git. If service-specific `.env` files already exist, keep their values consistent with the root file.

Start a tunnel in another terminal:

```bash
ngrok http 5001
```

Put its HTTPS forwarding address in `PUBLIC_BASE_URL`, without a trailing slash. Then start the bot from the repository root:

```bash
cd whatsapp-service
uv run python app.py
```

In the Twilio Sandbox settings, set the incoming-message webhook to `https://your-public-tunnel-host/webhook` and choose **POST**. Keep the server and tunnel running, then join the sandbox from WhatsApp.

If the tunnel address changes, update both Twilio and `PUBLIC_BASE_URL`, then restart the bot. The bot calls the recommendation engine directly through Python imports, so the separate FastAPI server is not required for this demo.

## Run the recommendation API separately

This lets you try recommendations without WhatsApp or audio. Its pinned dependencies use a separate environment; use Python **3.12** for this service.

From the repository root:

```bash
cd recommendation-service
uv venv .venv --python 3.12
uv pip install --python .venv/bin/python -r requirements.txt uvicorn
.venv/bin/python -m uvicorn app.api:app --reload --port 8000
```

The service needs `GROQ_API_KEY` in the root `.env` or a service-local `.env`. The command installs `uvicorn` explicitly because the requirements file does not include it.

Open `http://localhost:8000/docs`, or send a request:

```bash
curl -X POST http://localhost:8000/recommend \
  -H 'Content-Type: application/json' \
  -d '{
    "transcript": "I am an electrician in Delhi. I completed class 12, do wiring and maintenance, and want a job.",
    "language_code": "en-IN",
    "top_k": 3
  }'
```

The response includes the profile, ranked qualifications, exact training matches when available, related local courses and a readable reply. `GET /` returns the service health response. This endpoint handles one transcript at a time; the guided WhatsApp conversation runs in the WhatsApp service.

## Finding your way around the code

| Location | Responsibility |
| --- | --- |
| `whatsapp-service/app.py` | Twilio webhook, Sarvam calls, audio delivery and recommendation handoff. |
| `whatsapp-service/conversation.py` | Questions, profile confirmation, edits and SQLite sessions. |
| `whatsapp-service/profile_adapter.py` | Converts conversational answers into the recommender's profile format. |
| `recommendation-service/app/` | Profile extraction, normalization, qualification matching, ranking and API. |
| `recommendation-service/data/` | NQR workbook and training catalogue. |
| `web-app/` | Next.js starter scaffold; the user and admin dashboards are not connected yet. |

To preview the web scaffold, run `npm ci` and `npm run dev` from `web-app/`, then open `http://localhost:3000`.

## Checks and common problems

From `recommendation-service/`, using the environment above:

```bash
.venv/bin/python -m pytest tests -q \
  --deselect=tests/test_full_system.py::test_conversation_flow \
  --deselect=tests/test_full_system.py::test_api_recommendation_endpoint
```

These checks exercise local recommendation behavior without calling Groq. A `GROQ_API_KEY` value is still required at import time; a placeholder works for these local checks. Run `.venv/bin/python -m pytest tests -q` with a working key and network access to include the two live API tests. They do not verify WhatsApp delivery or Sarvam audio.

| Problem | What to check |
| --- | --- |
| WhatsApp does not reply | Sandbox membership, the running Flask server, and the current tunnel's `/webhook` URL using POST. |
| Audio conversion fails | Run `ffmpeg -version` to check the installation. |
| Reply audio cannot be fetched | Check `PUBLIC_BASE_URL` and public access to `/audio/reply.mp3`. |
| Groq or Sarvam returns an error | Check server output, credentials, account access to the model named in the code, and service limits. |
| No local centre appears | Check the catalogue's location, trade and `verified_at` fields. Old or unmatched rows are filtered out. |
| An old conversation resumes | Sessions survive restarts. After recommendations, send `start over`. |

When started as above, the bot stores sessions in `whatsapp-service/sessions.db` and audio in `whatsapp-service/audio_files/`. These contain conversation data and should stay out of commits.

## What we still need to finish

The next major piece is reliable provider coverage: exact course mappings, current batches, eligibility and usable admission links. Local employment and enterprise opportunity data are also needed to support livelihood advice beyond course suggestions.

The demo processes voice requests synchronously and uses a shared reply-audio filename, so handling concurrent users reliably still needs work. Regional-language text detection, consistent English text replies, web dashboards and IVR access are also unfinished.

For now, AASRA-AI helps someone describe their background and explore relevant training. Actual admission, scheme eligibility and placement still need to be checked with the responsible provider.
