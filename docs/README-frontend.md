# CheckIn Frontend

This is the frontend for the CheckIn voice companion application.

## Deployment

This frontend is automatically deployed to GitHub Pages using GitHub Actions.

### Live Site
🌐 [https://aanyabharadwaj.github.io/Teen-Health-App/](https://aanyabharadwaj.github.io/Teen-Health-App/)

### Backend Connection
The frontend connects to the backend deployed on Render:
- **Backend URL**: https://teen-health-app-1.onrender.com
- **WebSocket URL**: wss://teen-health-app-1.onrender.com/ws

## Features

- 🎤 Voice-based conversation with AI companion
- 🧠 Mood tracking and personalized responses
- 📱 Mobile-responsive design
- 🎨 Beautiful animated UI with floating bubbles
- 🔒 Privacy-focused with local-first approach

## Technology Stack

- **Frontend**: Vanilla HTML, CSS, JavaScript
- **Backend**: Python with Pipecat AI framework
- **Deployment**: GitHub Pages (frontend) + Render (backend)
- **AI Services**: Deepgram (STT/TTS), Google Gemini (LLM)

## Development

To run locally:

1. Clone the repository
2. Start the backend: `python server.py`
3. Open `docs/index.html` in your browser
4. Set `DEPLOY_MODE = 'local'` in the JavaScript

## Support

For mental health support, please use the crisis resources available in the app.



