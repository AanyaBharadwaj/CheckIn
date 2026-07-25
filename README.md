# CheckIn Real-Time Voice Companion

A real-time voice conversation system for teen mental health support.
Built with Pipecat, Deepgram, and Gemini.

## Features

- **6-Screen Onboarding**: Welcome, Profile, Disclaimer, Greeting, Conversation, Goodbye
- **Personalized Experience**: Collects name, age, and mood — AI adapts tone and greeting
- **Natural Conversation**: Speak naturally, pause when done — AI responds automatically
- **Low Latency**: Real-time audio streaming via WebSocket
- **Voice Activity Detection**: Automatically detects when you start/stop speaking
- **Interruptible**: You can interrupt the AI while it's speaking
- **Topic Chips**: Quick-start conversation topics (School, Friends, Family, Feelings)
- **Crisis Safety**: 988 Suicide & Crisis Lifeline link always accessible

## Setup

### 1. Install Dependencies

```bash
cd realtime
pip install -r requirements.txt
```

### 2. Configure API Keys

Create a `.env` file in the parent directory:

```
DEEPGRAM_API_KEY=your_deepgram_key
GEMINI_API_KEY=your_gemini_key
```

### 3. Run

```bash
./run.sh
```

Or manually:

```bash
# Terminal 1 — Voice server
python server.py

# Terminal 2 — Frontend
python -m http.server 8080 --directory frontend
```

Then open http://localhost:8080

## User Flow

1. **Welcome** — Landing page with CheckIn branding
2. **Profile** — Enter name, select age (13–19), pick mood
3. **Disclaimer** — Consent checkbox (not a therapist, conversations not stored)
4. **Greeting** — Animated "Hi {name}!" adapts to mood
5. **Conversation** — Voice chat with real-time transcription
6. **Goodbye** — Personalized farewell with option to restart

## Architecture

```
Browser (WebSocket) ←→ Pipecat Server ←→ Deepgram / Gemini

Frontend sends:                Server pipeline:
  user_metadata JSON  ──→      Metadata → Personalized prompt
  raw Int16 audio     ──→      VAD → STT (Deepgram Nova-2)
                                       → LLM (Gemini 2.5 Flash)
  audio + JSON        ←──             → TTS (Deepgram Aura)
```

## Tech Stack

- **Pipecat** — Voice AI pipeline framework
- **Deepgram Nova-2** — Speech-to-text
- **Deepgram Aura** — Text-to-speech
- **Gemini 2.5 Flash** — Language model
- **Silero VAD** — Voice activity detection
- **Vanilla JS** — Single-file frontend, no build step

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Connection failed | Make sure `python server.py` is running on port 8765 |
| No microphone | Allow mic permissions in browser, use Chrome |
| Echo/feedback | Use headphones |
| Server won't start | Check `.env` has valid API keys |
