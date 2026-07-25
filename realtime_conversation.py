"""Real-time conversational voice module.

This module provides a natural conversation experience with:
- Simple record → process → respond flow
- Deepgram Nova-2 STT for transcription
- Deepgram Aura TTS for natural AI voice responses
- Auto-play responses for seamless conversation
"""

import streamlit as st
import requests
import base64
import json
import io
from typing import Optional, Tuple
from config import DEEPGRAM_API_KEY, GEMINI_API_KEY
import google.generativeai as genai

# Deepgram API endpoints
DEEPGRAM_STT_URL = "https://api.deepgram.com/v1/listen"
DEEPGRAM_TTS_URL = "https://api.deepgram.com/v1/speak"


def transcribe_audio(audio_bytes: bytes) -> Tuple[Optional[str], Optional[str]]:
    """Transcribe audio using Deepgram Nova-2."""
    if not DEEPGRAM_API_KEY:
        return None, "Deepgram API key not configured"

    try:
        # Detect audio format from header
        content_type = "audio/wav"
        if audio_bytes[:4] == b'RIFF':
            content_type = "audio/wav"
        elif audio_bytes[:3] == b'ID3' or audio_bytes[:2] == b'\xff\xfb':
            content_type = "audio/mp3"
        elif audio_bytes[:4] == b'OggS':
            content_type = "audio/ogg"
        elif audio_bytes[:4] == b'fLaC':
            content_type = "audio/flac"

        url = f"{DEEPGRAM_STT_URL}?model=nova-2&smart_format=true&language=en"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": content_type
        }

        response = requests.post(url, headers=headers, data=audio_bytes, timeout=30)

        if response.status_code == 200:
            result = response.json()
            transcript = (result.get("results", {})
                         .get("channels", [{}])[0]
                         .get("alternatives", [{}])[0]
                         .get("transcript", ""))
            confidence = (result.get("results", {})
                         .get("channels", [{}])[0]
                         .get("alternatives", [{}])[0]
                         .get("confidence", 0))

            if transcript:
                return transcript.strip(), None
            return None, f"No speech detected (confidence: {confidence:.2f})"
        else:
            return None, f"Deepgram error: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return None, f"Transcription error: {str(e)}"


def text_to_speech(text: str) -> Tuple[Optional[bytes], Optional[str]]:
    """Convert text to speech using Deepgram Aura."""
    if not DEEPGRAM_API_KEY:
        return None, "Deepgram API key not configured"

    try:
        # Use Aura Asteria voice (warm, friendly female voice)
        url = f"{DEEPGRAM_TTS_URL}?model=aura-asteria-en"
        headers = {
            "Authorization": f"Token {DEEPGRAM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"text": text}

        response = requests.post(url, headers=headers, json=payload, timeout=30)

        if response.status_code == 200:
            return response.content, None
        else:
            return None, f"TTS error: {response.status_code} - {response.text[:100]}"
    except Exception as e:
        return None, f"TTS error: {str(e)}"


def get_ai_response(user_message: str, conversation_history: list) -> Tuple[Optional[str], Optional[str]]:
    """Get AI response from Gemini."""
    if not GEMINI_API_KEY:
        return None, "Gemini API key not configured"

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')

        # Build context from history
        context_messages = []
        for msg in conversation_history[-6:]:  # Last 6 messages for context
            role = "User" if msg['role'] == 'user' else "CheckIn"
            context_messages.append(f"{role}: {msg['content']}")

        context = "\n".join(context_messages) if context_messages else ""

        prompt = f"""You are CheckIn, a supportive and empathetic companion for teenagers.

IMPORTANT RULES:
- Keep responses SHORT (1-3 sentences max) - this is a voice conversation
- Be warm, friendly, and conversational
- Use natural speech patterns (contractions, casual language)
- If someone seems distressed, be supportive and gently suggest talking to a trusted adult
- Never lecture or be preachy
- Match the user's energy and tone

Previous conversation:
{context}

User just said: "{user_message}"

Respond naturally and briefly:"""

        response = model.generate_content(prompt)
        return response.text.strip(), None
    except Exception as e:
        error_msg = str(e)
        if "403" in error_msg:
            return None, "API key issue - please check your Gemini API key"
        return None, f"AI error: {error_msg}"


def render_realtime_conversation_ui():
    """Render the real-time conversation UI."""

    # Initialize conversation history
    if 'rt_conversation' not in st.session_state:
        st.session_state.rt_conversation = []
    if 'rt_last_audio' not in st.session_state:
        st.session_state.rt_last_audio = None

    # Custom CSS
    st.markdown("""
    <style>
    .convo-container {
        max-height: 350px;
        overflow-y: auto;
        padding: 15px;
        background: linear-gradient(180deg, #0a0a1a 0%, #0f0f2a 100%);
        border-radius: 16px;
        margin: 15px 0;
        border: 1px solid rgba(0, 212, 255, 0.2);
    }
    .msg-bubble {
        padding: 12px 16px;
        border-radius: 16px;
        margin: 8px 0;
        max-width: 85%;
        animation: slideIn 0.3s ease;
    }
    .user-msg {
        background: linear-gradient(135deg, #1e3a5f 0%, #2d1b4e 100%);
        margin-left: auto;
        border-bottom-right-radius: 4px;
        color: #e0e8ff;
        text-align: right;
    }
    .ai-msg {
        background: linear-gradient(135deg, #0d3d3d 0%, #1a4a3a 100%);
        margin-right: auto;
        border-bottom-left-radius: 4px;
        color: #e0fff0;
    }
    .msg-label {
        font-size: 10px;
        opacity: 0.5;
        margin-bottom: 4px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    @keyframes slideIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .voice-instructions {
        background: linear-gradient(135deg, rgba(0, 212, 255, 0.08), rgba(0, 255, 136, 0.08));
        border: 1px solid rgba(0, 212, 255, 0.2);
        border-radius: 12px;
        padding: 15px;
        margin: 10px 0;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; margin: 15px 0;">
        <h3 style="color: #00d4ff; margin-bottom: 8px;">Live Voice Conversation</h3>
        <p style="opacity: 0.6; font-size: 13px;">
            Record your message → Get an instant voice response
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Display conversation history
    if st.session_state.rt_conversation:
        convo_html = '<div class="convo-container">'
        for msg in st.session_state.rt_conversation:
            if msg['role'] == 'user':
                convo_html += f'''
                <div class="msg-bubble user-msg">
                    <div class="msg-label">You</div>
                    {msg['content']}
                </div>'''
            else:
                convo_html += f'''
                <div class="msg-bubble ai-msg">
                    <div class="msg-label">CheckIn</div>
                    {msg['content']}
                </div>'''
        convo_html += '</div>'
        st.markdown(convo_html, unsafe_allow_html=True)

        # Auto-scroll script
        st.markdown("""
        <script>
            const container = document.querySelector('.convo-container');
            if (container) container.scrollTop = container.scrollHeight;
        </script>
        """, unsafe_allow_html=True)

    # Instructions
    st.markdown("""
    <div class="voice-instructions">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 8px;">
            <span style="font-size: 20px;">🎙️</span>
            <span style="color: #00d4ff; font-weight: 600;">How it works:</span>
        </div>
        <ol style="margin: 0; padding-left: 25px; font-size: 13px; color: #aaa; line-height: 1.8;">
            <li>Click the <b>microphone button</b> below to record</li>
            <li>Speak your message, then click <b>stop</b></li>
            <li>Your message will be transcribed and I'll respond with voice!</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

    # Audio input using Streamlit's native component
    audio_value = None

    # Check if st.audio_input is available
    if hasattr(st, 'audio_input'):
        audio_value = st.audio_input(
            "🎤 Record your message",
            key="rt_voice_input"
        )
    else:
        # Fallback to file uploader
        audio_value = st.file_uploader(
            "🎤 Upload or record audio",
            type=["wav", "mp3", "m4a", "ogg", "webm"],
            key="rt_voice_upload"
        )

    # Process audio when available
    if audio_value is not None:
        audio_bytes = audio_value.getvalue() if hasattr(audio_value, 'getvalue') else audio_value.read()

        # Check if this is new audio (not the same as last processed)
        audio_hash = hash(audio_bytes[:1000]) if len(audio_bytes) > 1000 else hash(audio_bytes)

        if st.session_state.rt_last_audio != audio_hash:
            st.session_state.rt_last_audio = audio_hash

            # Show processing status
            with st.status("Processing your message...", expanded=True) as status:
                st.write("🎧 Transcribing audio...")
                transcript, error = transcribe_audio(audio_bytes)

                if error:
                    status.update(label="Transcription failed", state="error")
                    st.error(f"Could not transcribe: {error}")
                elif not transcript:
                    status.update(label="No speech detected", state="error")
                    st.warning("I didn't catch that. Please try speaking more clearly.")
                else:
                    # Add user message
                    st.session_state.rt_conversation.append({
                        'role': 'user',
                        'content': transcript
                    })
                    st.write(f"✅ You said: \"{transcript}\"")

                    # Get AI response
                    st.write("🤔 Thinking...")
                    response, ai_error = get_ai_response(transcript, st.session_state.rt_conversation)

                    if ai_error:
                        status.update(label="AI error", state="error")
                        st.error(f"Could not generate response: {ai_error}")
                    else:
                        # Add AI response
                        st.session_state.rt_conversation.append({
                            'role': 'assistant',
                            'content': response
                        })
                        st.write(f"💬 Response: \"{response}\"")

                        # Generate TTS
                        st.write("🔊 Generating voice...")
                        tts_audio, tts_error = text_to_speech(response)

                        if tts_error:
                            st.warning(f"Voice generation failed: {tts_error}")
                            status.update(label="Response ready (text only)", state="complete")
                        else:
                            status.update(label="Response ready!", state="complete")

                            # Store TTS audio for playback
                            st.session_state.rt_tts_audio = tts_audio

            # Rerun to show updated conversation
            st.rerun()

    # Play TTS audio if available
    if 'rt_tts_audio' in st.session_state and st.session_state.rt_tts_audio:
        st.markdown("### 🔊 AI Response")
        st.audio(st.session_state.rt_tts_audio, format="audio/mp3", autoplay=True)

        # Clear after showing once
        if st.button("🎤 Record Next Message", type="primary", use_container_width=True):
            st.session_state.rt_tts_audio = None
            st.rerun()

    # Control buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.session_state.rt_conversation:
            if st.button("🗑️ Clear Conversation", use_container_width=True):
                st.session_state.rt_conversation = []
                st.session_state.rt_last_audio = None
                st.session_state.rt_tts_audio = None
                st.rerun()

    with col2:
        if st.session_state.rt_conversation:
            # Show conversation count
            msg_count = len(st.session_state.rt_conversation)
            st.markdown(f"<p style='text-align: center; color: #666; padding: 10px;'>{msg_count} messages</p>", unsafe_allow_html=True)


def stop_realtime_conversation():
    """Stop the conversation session."""
    if 'rt_conversation' in st.session_state:
        st.session_state.rt_conversation = []
    if 'rt_last_audio' in st.session_state:
        st.session_state.rt_last_audio = None
    if 'rt_tts_audio' in st.session_state:
        st.session_state.rt_tts_audio = None


def is_realtime_conversation_available() -> bool:
    """Check if real-time conversation is available."""
    return bool(DEEPGRAM_API_KEY and GEMINI_API_KEY)
