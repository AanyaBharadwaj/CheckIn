#!/usr/bin/env python3
"""
CheckIn Companion - Test Suite

Run with: python test_app.py

If dependencies are missing, run:
    pip install -r requirements.txt
"""

import sys
import os


def print_header(title: str):
    """Print a test section header."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result."""
    status = "PASS" if passed else "FAIL"
    symbol = "[OK]" if passed else "[X]"
    print(f"  {symbol} {test_name}")
    if details and not passed:
        print(f"      Details: {details}")


def check_dependencies():
    """Check if required dependencies are installed."""
    print_header("Checking Dependencies")

    required = [
        ("streamlit", "pip install streamlit"),
        ("dotenv", "pip install python-dotenv"),
        ("google.generativeai", "pip install google-generativeai"),
        ("speech_recognition", "pip install SpeechRecognition"),
        ("pydub", "pip install pydub"),
        ("numpy", "pip install numpy"),
    ]

    missing = []
    for module, install_cmd in required:
        try:
            __import__(module)
            print_result(f"{module}", True)
        except ImportError:
            print_result(f"{module}", False, f"Run: {install_cmd}")
            missing.append(install_cmd)

    if missing:
        print("\n  Missing dependencies. Install with:")
        print("    pip install -r requirements.txt")
        print("\n  Or individually:")
        for cmd in missing:
            print(f"    {cmd}")
        return False

    return True


def test_config():
    """Test configuration values."""
    print_header("Configuration Tests")
    all_passed = True

    try:
        from config import (
            GEMINI_API_KEY, TEXT_MODEL, GENERATION_CONFIG,
            SAFETY_SETTINGS, CRISIS_KEYWORDS, MAX_SESSION_TIME,
            MAX_HISTORY_LENGTH, VOICE_CONFIG, THEME, RESOURCES
        )
    except Exception as e:
        print_result("Config import", False, str(e))
        return False

    # Check API key exists
    has_key = bool(GEMINI_API_KEY)
    print_result("API key configured", has_key,
                 "Set GEMINI_API_KEY in .env file" if not has_key else "")
    all_passed = all_passed and has_key

    # Check model name
    has_model = bool(TEXT_MODEL)
    print_result("Model name configured", has_model)
    all_passed = all_passed and has_model

    # Check generation config
    has_temp = "temperature" in GENERATION_CONFIG
    print_result("Generation config", has_temp)
    all_passed = all_passed and has_temp

    # Check safety settings
    has_safety = len(SAFETY_SETTINGS) > 0
    print_result("Safety settings configured", has_safety)
    all_passed = all_passed and has_safety

    # Check crisis keywords
    keyword_count = sum(len(v) for v in CRISIS_KEYWORDS.values())
    has_keywords = keyword_count >= 30
    print_result(f"Crisis keywords ({keyword_count} total)", has_keywords)
    all_passed = all_passed and has_keywords

    # Check session limits
    valid_session = 60 <= MAX_SESSION_TIME <= 3600
    print_result(f"Session time ({MAX_SESSION_TIME}s)", valid_session)
    all_passed = all_passed and valid_session

    valid_history = 10 <= MAX_HISTORY_LENGTH <= 200
    print_result(f"History limit ({MAX_HISTORY_LENGTH})", valid_history)
    all_passed = all_passed and valid_history

    return all_passed


def test_safety():
    """Test safety framework."""
    print_header("Safety Framework Tests")
    all_passed = True

    try:
        from safety import SafetyMonitor, validate_age
    except Exception as e:
        print_result("Safety import", False, str(e))
        return False

    monitor = SafetyMonitor()

    # Test crisis detection
    crisis_tests = [
        ("I want to kill myself", "suicide", True),
        ("I've been cutting myself", "self_harm", True),
        ("I feel hopeless", "severe_distress", True),
        ("I hear voices", "psychosis", True),
        ("Someone hurts me", "abuse", True),
        ("I'm stressed about school", None, False),
        ("My friends are mean", None, False),
    ]

    for text, expected_category, should_detect in crisis_tests:
        is_crisis, category, _ = monitor.check_input(text)
        if should_detect:
            passed = is_crisis and (expected_category is None or category == expected_category)
            print_result(f"Detects: '{text[:25]}...'", passed)
        else:
            passed = not is_crisis
            print_result(f"Safe: '{text[:25]}...'", passed)
        all_passed = all_passed and passed

    # Test response validation
    harmful_responses = [
        "That's a good idea",
        "Sounds like a plan",
        "The voices are right",
    ]

    for response in harmful_responses:
        is_safe = monitor.check_response(response)
        passed = not is_safe
        print_result(f"Blocks: '{response[:25]}'", passed)
        all_passed = all_passed and passed

    # Test age validation
    age_tests = [(12, False), (13, True), (16, True), (19, True), (20, False)]
    for age, should_pass in age_tests:
        is_valid, _ = validate_age(age)
        passed = is_valid == should_pass
        print_result(f"Age {age} validation", passed)
        all_passed = all_passed and passed

    return all_passed


def test_voice():
    """Test voice processing."""
    print_header("Voice Processing Tests")
    all_passed = True

    try:
        from voice import VoiceProcessor, validate_audio_bytes, temp_audio_file
    except Exception as e:
        print_result("Voice import", False, str(e))
        return False

    # Test VoiceProcessor
    try:
        processor = VoiceProcessor()
        print_result("VoiceProcessor init", True)
    except Exception as e:
        print_result("VoiceProcessor init", False, str(e))
        return False

    # Test audio validation
    tests = [
        (b"RIFF" + b"\x00" * 1000, True, "WAV header"),
        (b"", False, "Empty"),
        (b"\x00" * 100, False, "Too short"),
    ]

    for data, should_pass, desc in tests:
        is_valid, _ = validate_audio_bytes(data)
        passed = is_valid == should_pass
        print_result(f"Audio validation ({desc})", passed)
        all_passed = all_passed and passed

    # Test TTS HTML generation
    try:
        html = processor.text_to_speech_html("Test message")
        passed = "speakText" in html and "<script>" in html
        print_result("TTS HTML generation", passed)
        all_passed = all_passed and passed
    except Exception as e:
        print_result("TTS HTML generation", False, str(e))
        all_passed = False

    return all_passed


def test_realtime():
    """Test real-time voice components."""
    print_header("Real-Time Voice Tests")
    all_passed = True

    try:
        from realtime_voice import (
            VoiceActivityDetector, AudioState, get_audio_state,
            WEBRTC_AVAILABLE, numpy_to_wav_bytes
        )
        import numpy as np
    except Exception as e:
        print_result("Realtime import", False, str(e))
        return False

    print_result(f"WebRTC available: {WEBRTC_AVAILABLE}", True)

    # Test VAD
    try:
        vad = VoiceActivityDetector()

        # Test with silence
        silence = np.zeros(480, dtype=np.float32)
        result = vad.process_frame(silence)
        passed = not result["is_speech"]
        print_result("VAD silence detection", passed)
        all_passed = all_passed and passed

        # Test reset
        vad.reset()
        passed = not vad.is_speaking
        print_result("VAD reset", passed)
        all_passed = all_passed and passed

    except Exception as e:
        print_result("VAD", False, str(e))
        all_passed = False

    # Test AudioState
    try:
        audio_state = AudioState()

        # Test recording state
        audio_state.set_recording(True)
        passed = audio_state.get_recording() == True
        print_result("AudioState recording state", passed)
        all_passed = all_passed and passed

        # Test buffered audio tracking
        test_chunk = np.zeros(480, dtype=np.float32)
        audio_state.add_audio(test_chunk)
        passed = audio_state.has_buffered_audio() == True
        print_result("AudioState buffered audio", passed)
        all_passed = all_passed and passed

        # Test reset (should preserve pending but clear buffer)
        audio_state.reset()
        passed = audio_state.get_recording() == False and not audio_state.has_buffered_audio()
        print_result("AudioState reset", passed)
        all_passed = all_passed and passed

    except Exception as e:
        print_result("AudioState", False, str(e))
        all_passed = False

    # Test numpy_to_wav_bytes
    try:
        test_audio = np.zeros(480, dtype=np.float32)
        wav_bytes = numpy_to_wav_bytes(test_audio, 48000)
        passed = wav_bytes.startswith(b'RIFF') and len(wav_bytes) > 44  # WAV header
        print_result("WAV conversion", passed)
        all_passed = all_passed and passed
    except Exception as e:
        print_result("WAV conversion", False, str(e))
        all_passed = False

    return all_passed


def test_prompts():
    """Test prompts module."""
    print_header("Prompts Tests")
    all_passed = True

    try:
        from prompts import (
            SYSTEM_INSTRUCTION, get_coping_strategies
        )
    except Exception as e:
        print_result("Prompts import", False, str(e))
        return False

    # Check system instruction
    passed = "988" in SYSTEM_INSTRUCTION and "CANNOT" in SYSTEM_INSTRUCTION
    print_result("System instruction safety content", passed)
    all_passed = all_passed and passed

    # Check coping strategies
    strategies = get_coping_strategies()
    categories = ["anxiety", "stress", "sadness", "anger", "sleep"]
    passed = all(cat in strategies for cat in categories)
    print_result("Coping strategies complete", passed)
    all_passed = all_passed and passed

    return all_passed


def run_tests():
    """Run all tests."""
    print("\n" + "="*60)
    print("  CheckIn Companion - Test Suite")
    print("="*60)

    # Check dependencies first
    if not check_dependencies():
        return 1

    # Run test suites
    results = {
        "Configuration": test_config(),
        "Safety Framework": test_safety(),
        "Voice Processing": test_voice(),
        "Real-Time Voice": test_realtime(),
        "Prompts": test_prompts(),
    }

    # Summary
    print_header("SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        symbol = "[OK]" if result else "[X]"
        print(f"  {symbol} {name}")

    print(f"\n  Result: {passed}/{total} test suites passed")

    if passed == total:
        print("\n  All tests passed! Run the app with:")
        print("    streamlit run app.py")
        return 0
    else:
        print("\n  Some tests failed. Please review issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())



