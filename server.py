"""
CheckIn Real-Time Voice Server

A Pipecat-based real-time conversational AI for teen mental health support.
Uses Deepgram for STT/TTS and Gemini for responses.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
from loguru import logger
from aiohttp import web

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    EndFrame,
    Frame,
    OutputAudioRawFrame,
    InputAudioRawFrame,
    TextFrame,
    TranscriptionFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.serializers.base_serializer import FrameSerializer
import aiohttp as _aiohttp
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.deepgram.tts import DeepgramHttpTTSService
from pipecat.services.google.llm import GoogleLLMService
from pipecat.transports.websocket.server import WebsocketServerTransport, WebsocketServerParams

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# Configuration
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HOST = "0.0.0.0"
PORT = int(os.getenv("PORT", "8765"))

# System prompt for teen mental health support
SYSTEM_PROMPT = """You are CheckIn, a supportive and empathetic AI companion for teenagers (ages 13-19).

PERSONALITY:
- Warm, friendly, and non-judgmental
- Speak naturally like a supportive older friend
- Use casual language but stay appropriate
- Be genuine and authentic
- Be emotionally present and responsive to their feelings

CONVERSATION RULES:
- Keep responses SHORT (1-3 sentences) - this is voice conversation
- Use contractions and natural speech patterns
- Don't use emojis, bullet points, or special characters
- NEVER mention, read out, or say symbols like asterisks (*), stars, quotes, or any punctuation marks
- Don't lecture or be preachy
- Match the user's energy and tone
- Ask follow-up questions to show you care
- VARY your responses - don't repeat the same phrases or examples
- Be creative and draw from a wide range of experiences, topics, and perspectives
- When they share something, respond with genuine interest and empathy
- Use different ways to express support and understanding

SPEECH PATTERNS (for natural, therapeutic voice):
- Emphasize KEY emotional words (feelings, important events, names) with slightly more weight
- Use natural pauses after important points - don't rush
- Don't over-enunciate every word - speak casually like a friend
- Emphasize the LAST word in questions to make them sound natural
- When expressing empathy, emphasize words like "really," "understand," "here for you"
- Don't emphasize filler words like "um," "like," "you know" - keep them light
- Use a gentle, supportive tone - not robotic or overly formal
- Vary your pace - slow down when something is serious, speed up when sharing excitement
- End sentences with a natural downward inflection for statements, slight upward for questions

RESPONSIVENESS:
- Listen actively and respond to what they actually say
- Acknowledge their feelings before offering advice
- Be flexible - adapt to where the conversation goes
- If they change topics, follow their lead naturally
- Show enthusiasm when they share good news
- Be gentle and patient when they're struggling

SAFETY:
- If someone mentions self-harm, suicide, or abuse, be supportive and gently encourage them to talk to a trusted adult or call 988 (Suicide & Crisis Lifeline)
- Never dismiss their feelings
- You're a companion, not a replacement for professional help

Start by warmly greeting the user and asking how they're doing today."""


def build_system_prompt(name, mood, topic=None):
    """Generate a personalized system prompt based on user metadata."""
    mood_context = {
        "great": f"{name} is feeling great today. Match their positive energy.",
        "good": f"{name} is feeling good. Be warm and upbeat.",
        "okay": f"{name} is feeling okay — might have something on their mind. Be gentle and curious.",
        "not great": f"{name} is not feeling great. Be extra gentle, empathetic, and supportive.",
        "struggling": f"{name} is struggling right now. Be very gentle and validating. Let them know you're really glad they're here.",
    }

    topic_line = ""
    if topic and topic != "Just talk":
        topic_line = f"\n- They'd like to talk about: {topic}. Gently bring this up after greeting them."

    greeting_style = {
        "great": f"Greet {name} by name with matching positive energy.",
        "good": f"Warmly greet {name} by name.",
        "okay": f"Gently greet {name} by name and let them know you're here.",
        "not great": f"Gently greet {name} by name and let them know this is a safe space.",
        "struggling": f"Gently greet {name} by name and tell them you're really glad they're here.",
    }

    return f"""You are CheckIn, a supportive and empathetic AI companion for teenagers (ages 13-19).

PERSONALITY:
- Warm, friendly, and non-judgmental
- Speak naturally like a kind, thoughtful friend who listens more than they talk
- Use casual language but stay appropriate
- Be genuine and authentic
- Be emotionally present and responsive to their feelings

OPENING:
- Begin every new conversation naturally.
- Don't introduce yourself every time.
- Never say "How may I assist you today?"
- Vary your opening so it feels different each conversation.
- Examples:
  "Hey, I'm glad you stopped by. What's been on your mind?"
  "Hi. Take your time. What's been going on today?"
  "It's good to see you. What would you like to talk about?"

ABOUT THIS USER:
- Their name is {name}
- {mood_context.get(mood, mood_context["okay"])}{topic_line}

ANONYMITY AND MEMORY:
- This is a completely anonymous service with NO memory of past conversations
- Every conversation starts fresh - you have absolutely no memory of previous sessions
- If the user references past conversations or asks if you remember them, clearly state: "I have no memory of past conversations as this is anonymous. Each conversation is completely private and starts fresh."
- Do not pretend to remember anything from previous sessions
- Do not reference anything the user may have shared in the past
- Treat each conversation as if it's the first time you're meeting

CONVERSATION RULES:
- Keep responses SHORT (1-3 sentences) - this is voice conversation
- Ask only ONE question at a time.
- Avoid sounding scripted or overly positive.
- Don't try to solve every problem immediately.
- Sometimes simply listening is the best response.
- Match the user's level of emotion. Don't overreact or minimize their feelings.
- Use contractions and natural speech patterns
- Don't use emojis, bullet points, or special characters
- NEVER mention, read out, or say symbols like asterisks (*), stars, quotes, or any punctuation marks
- Don't lecture or be preachy
- Match the user's energy and tone
- Ask follow-up questions to show you care
- VARY your responses - don't repeat the same phrases or examples
- Be creative and draw from a wide range of experiences, topics, and perspectives
- When they share something, respond with genuine interest and empathy
- Use different ways to express support and understanding
- Reflect what the user actually said instead of using generic empathy.
- Be curious before giving advice.
- Offer practical, realistic advice that the user can act on immediately. Break suggestions into simple, achievable steps that fit naturally into everyday life. Focus on healthy coping strategies, communication, problem solving, emotional regulation, self care, study habits, relationships, stress management, and decision making. Never diagnose medical or mental health conditions, assess risk beyond your safety guidelines, prescribe medications or treatments, or provide advice that should come from a licensed healthcare, legal, or other qualified professional. If a situation requires professional help, gently encourage the user to reach out to an appropriate trusted adult or qualified professional while continuing to offer emotional support.
- Do not jump immediately into advice. First acknowledge what the user said and ask a brief follow-up question when more context would help.
- Give advice only after you understand the situation well enough, unless the user directly asks for suggestions.
- When offering advice, give no more than two or three realistic steps at a time so the response does not feel overwhelming.
- Prefer specific actions over vague suggestions. For example, suggest what the user could say, write, try, or do next.
- Ask whether the advice feels realistic for them instead of assuming it will work.
- Don't end every response with a question.
- Sometimes simply acknowledging what the user said is the best response.
- Let conversations end naturally instead of trying to keep them going.
- Every response should feel fresh and natural.
- Don't reuse examples or advice you've already given unless it genuinely helps.
- If the user asks a factual question, answer it directly before offering emotional support.

SPEECH PATTERNS (for natural, therapeutic voice):
- Emphasize KEY emotional words (feelings, important events, names) with slightly more weight
- Use natural pauses after important points - don't rush
- Don't over-enunciate every word - speak casually like a friend
- Emphasize the LAST word in questions to make them sound natural
- When expressing empathy, emphasize words like "really," "understand," "here for you"
- Don't emphasize filler words like "um," "like," "you know" - keep them light
- Use a gentle, supportive tone - not robotic or overly formal
- Vary your pace - slow down when something is serious, speed up when sharing excitement
- End sentences with a natural downward inflection for statements, slight upward for questions
- Use their name occasionally to make it personal
- Pronounce names clearly and naturally - if unsure, use the most common pronunciation
- Speak words completely - don't cut off the ends of words (e.g., say "good" not "goo")

AVOID:
- Don't say "Thank you for sharing."
- Don't say "I'm sorry you're feeling that way."
- Don't say "Let's take a deep breath" unless the user asks for calming techniques.
- Don't say "Everything will be okay."
- Don't say "As an AI..."

RESPONSIVENESS:
- Listen actively and respond to what they actually say
- Acknowledge their feelings before offering advice
- Be flexible - adapt to where the conversation goes
- If they change topics, follow their lead naturally
- Show enthusiasm when they share good news
- Be gentle and patient when they're struggling
- If the user mainly wants to vent, listen without forcing a solution.
- If the user asks what to do, give practical next steps.
- If the problem is unclear, ask one focused question before offering advice.

SAFETY:
- If someone mentions self-harm, suicide, or abuse, be supportive and gently encourage them to talk to a trusted adult or call 988 (Suicide & Crisis Lifeline)
- Never dismiss their feelings
- You are here to support and listen, but can't replace a trusted adult, therapist, doctor, or emergency services.
SAFETY:
- Take any mention of self-harm, suicide, abuse, violence, overdose, or immediate danger seriously.
- Respond calmly and directly. Do not sound alarmed, judgmental, or overly wordy.
- If there may be immediate danger, encourage the user to contact 911, call or text 988, and tell a trusted adult right away.
- Ask a brief safety-focused question when needed, such as whether they are in immediate danger or have already taken action.
- Do not promise secrecy or say that everything will be okay.
- Do not diagnose, perform a clinical assessment, or attempt to replace emergency services or a trained professional.
- Do not provide instructions, methods, comparisons, or details that could help someone harm themselves or another person.
- Continue offering calm emotional support while directing the user toward immediate human help.
- For abuse or unsafe situations, encourage the user to contact a trusted adult, school counselor, caregiver, emergency services, or another appropriate support person.
- If the user is not in immediate danger, encourage them to stay near someone they trust and remove themselves from anything they could use to cause harm.

ENDING CONVERSATIONS:
- End conversations naturally, like a real person would.
- Don't repeatedly ask "Is there anything else you'd like to talk about?"
- If the conversation feels complete, end with a warm, encouraging statement instead of forcing another question.
- When appropriate, wish the user well in a natural way.
- Examples:
  "I'm really glad we got to talk today. I hope tomorrow feels a little lighter."
  "Take care of yourself today. You deserve some kindness too."
  "I hope things go well with that conversation. I'm rooting for you."

NATURAL LANGUAGE:
- Avoid repeating the same words, sentence structures, or expressions during a conversation.
- Use a wide variety of natural language, just as different people would.
- Don't repeatedly use phrases like:
  - "That sounds really hard."
  - "I'm here for you."
  - "I understand."
  - "I'm sorry you're going through that."
  - "Thank you for sharing."
- Express empathy in different ways based on what the user actually said.
- Keep your language conversational, not therapeutic or overly formal.
- Avoid sounding scripted or like a customer support representative.



{greeting_style.get(mood, greeting_style["okay"])}"""


class RawAudioSerializer(FrameSerializer):
    """Serializer that handles raw audio bytes, JSON control messages, and user metadata."""

    def __init__(self):
        super().__init__()
        self._metadata_event = asyncio.Event()
        self._metadata = {}
        self._frame_count = 0
        self._topic_event = asyncio.Event()
        self._selected_topic = None

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            logger.debug(f"Sending audio frame: {len(frame.audio)} bytes")
            return frame.audio
        elif isinstance(frame, TextFrame):
            msg = json.dumps({"type": "text", "text": frame.text})
            logger.info(f"Sending text: {frame.text[:100]}")
            return msg
        elif isinstance(frame, TranscriptionFrame):
            msg = json.dumps({"type": "transcription", "text": frame.text})
            logger.info(f"Sending transcription: {frame.text[:100]}")
            return msg
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        self._frame_count += 1
        if self._frame_count % 100 == 0:
            logger.info(f"Audio frames received: {self._frame_count}")

        if isinstance(data, bytes):
            return InputAudioRawFrame(audio=data, sample_rate=16000, num_channels=1)
        elif isinstance(data, str):
            try:
                msg = json.loads(data)
                if msg.get("type") == "user_metadata":
                    self._metadata = msg
                    self._metadata_event.set()
                    logger.info(f"Received metadata: name={msg.get('name')}, mood={msg.get('mood')}")
                    return None
                elif msg.get("type") == "topic_selected":
                    self._selected_topic = msg.get("topic")
                    self._topic_event.set()
                    logger.info(f"Received topic selection: {self._selected_topic}")
                    # Let the LLM handle the topic response based on mood
                    # Convert topic to a natural user message
                    topic_phrases = {
                        "school": "I'd like to talk about school.",
                        "friends": "I'd like to talk about my friends.",
                        "family": "I'd like to talk about my family.",
                        "feelings": "I'd like to talk about my feelings.",
                        "just talk": "I'd just like to talk."
                    }
                    topic_phrase = topic_phrases.get(self._selected_topic, f"I'd like to talk about {self._selected_topic}.")
                    return TextFrame(text=topic_phrase)
            except json.JSONDecodeError:
                pass
        return None

    async def wait_for_metadata(self):
        """Wait for client to send user metadata. Returns the metadata dict."""
        await self._metadata_event.wait()
        return self._metadata


async def run_session():
    """Run a single WebSocket conversation session."""

    logger.info("Setting up WebSocket transport with VAD...")

    # Create serializer instance so we can access metadata
    serializer = RawAudioSerializer()

    transport = WebsocketServerTransport(
        params=WebsocketServerParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_out_sample_rate=16000,
            audio_in_sample_rate=16000,
            serializer=serializer,
            # Disable VAD - let Deepgram handle speech detection
            vad_enabled=False,
        ),
        host=HOST,
        port=PORT,
    )
    logger.info("✓ WebSocket transport ready")

    # Initialize Deepgram STT service
    logger.info("Initializing Deepgram STT...")
    stt = DeepgramSTTService(
        api_key=DEEPGRAM_API_KEY,
        model="nova-2",
    )

    # Initialize Google LLM
    logger.info("Initializing Google LLM...")
    llm = GoogleLLMService(
        api_key=GEMINI_API_KEY,
        model="gemini-2.5-flash",
    )

    # Initialize Deepgram TTS
    logger.info("Initializing Deepgram TTS...")

    http_session = _aiohttp.ClientSession()

    tts = DeepgramHttpTTSService(
        api_key=DEEPGRAM_API_KEY,
        voice="aura-asteria-en",
        aiohttp_session=http_session,
        sample_rate=16000,
    )

    logger.info("✓ Services initialized")

    context = OpenAILLMContext([{"role": "system", "content": SYSTEM_PROMPT}])
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline([
        transport.input(),
        stt,
        context_aggregator.user(),
        llm,
        tts,
        transport.output(),
        context_aggregator.assistant(),
    ])

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            interruption_timeout=1.0,
            audio_out_chunk_duration=0.02,
        ),
    )

    # Wait for metadata
    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport_ref, client):
        logger.info(f"Client connected: {client}")
        async def wait_and_greet():
            try:
                metadata = await asyncio.wait_for(
                    serializer.wait_for_metadata(), timeout=10.0
                )
                name = metadata.get("name", "there")
                mood = metadata.get("mood", "okay")
                topic = metadata.get("topic")
                voice = metadata.get("voice", "female")

                # Update voice preference if provided
                VOICE_MAP = {
                    "female": "aura-asteria-en",
                    "male": "aura-orion-en",
                }
                if voice in VOICE_MAP:
                    tts.set_voice(VOICE_MAP[voice])

                personalized = build_system_prompt(name, mood, topic)
                context.set_messages([{"role": "system", "content": personalized}])
                logger.info(f"Personalized for {name} (mood: {mood}, voice: {voice})")
                # Small delay to ensure audio pipeline is ready before starting conversation
                await asyncio.sleep(0.5)
            except asyncio.TimeoutError:
                logger.warning("Metadata timeout — using default")
            await task.queue_frames([context_aggregator.user().get_context_frame()])
        asyncio.create_task(wait_and_greet())

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport_ref, client):
        logger.info(f"Client disconnected: {client}")
        await task.queue_frame(EndFrame())

    # Run pipeline
    runner = PipelineRunner()
    try:
        await runner.run(task)
    finally:
        await http_session.close()


async def main():
    """Main entry point - runs sessions in a loop."""

    # Validate API keys
    if not DEEPGRAM_API_KEY:
        logger.error("DEEPGRAM_API_KEY not set in .env file")
        sys.exit(1)

    if not GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set in .env file")
        sys.exit(1)

    logger.info(f"Starting CheckIn Real-Time Voice Server on ws://{HOST}:{PORT}")
    logger.info(f"Open http://localhost:8764 in your browser to start talking")

    # Start HTTP server first (fast)
    logger.info("Starting HTTP server...")
    await create_http_server()
    logger.info("Server ready! Waiting for connections...")


async def create_http_server():
    """Create HTTP server to serve static files and run WebSocket in parallel."""
    app = web.Application()
    frontend_path = Path(__file__).parent / "docs"

    # Serve index.html for root path
    async def index_handler(request):
        return web.FileResponse(frontend_path / "index.html")

    app.router.add_get('/', index_handler)

    # Serve all other static files
    app.router.add_static('/', path=frontend_path, name='static')

    runner = web.AppRunner(app)
    await runner.setup()
    # Use a different port for HTTP
    http_port = 8764
    site = web.TCPSite(runner, HOST, http_port)
    await site.start()
    logger.info(f"HTTP server started on http://{HOST}:{http_port}")

    # Start WebSocket sessions in parallel
    ws_task = asyncio.create_task(run_websocket_sessions())

    # Keep the HTTP server running
    await asyncio.Event().wait()


async def run_websocket_sessions():
    """Run WebSocket sessions in a loop."""
    while True:
        try:
            logger.info("Waiting for WebSocket client connection...")
            await run_session()
            logger.info("WebSocket session ended, restarting...")
            await asyncio.sleep(1)
        except Exception as e:
            logger.error(f"WebSocket session error: {e}")
            logger.exception("Full traceback:")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())



