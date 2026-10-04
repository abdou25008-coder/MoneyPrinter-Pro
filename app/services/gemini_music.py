import math
import os
import random
import wave
import struct
from loguru import logger
from app.config import config
from app.utils import utils

def analyze_music_mood_with_gemini(subject: str, script: str) -> dict:
    """
    Uses Gemini LLM to analyze the narrative tone and recommend musical properties:
    mood, key, tempo (BPM), and intensity profile.
    """
    api_key = config.gemini.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        return {
            "mood": "epic documentary",
            "tempo_bpm": 100,
            "style": "cinematic ambient",
            "intensity": "medium"
        }

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        prompt = (
            f"Analyze this video script and topic for sound design and background music composition.\n"
            f"Topic: {subject}\n"
            f"Script: {script[:800]}\n\n"
            f"Return ONLY a JSON object with:\n"
            f'{{"mood": "mood description", "tempo_bpm": number (60-140), "style": "ambient/orchestral/synth/dramatic", "intensity": "low/medium/high"}}'
        )
        response = client.models.generate_content(
            model=config.gemini.get("model_name") or "gemini-1.5-flash",
            contents=prompt,
        )
        text = response.text.strip()
        import json
        import re
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception as exc:
        logger.warning(f"Gemini music analysis fallback: {exc}")

    return {
        "mood": "cinematic atmospheric",
        "tempo_bpm": 95,
        "style": "ambient",
        "intensity": "medium"
    }

def synthesize_procedural_gemini_bgm(output_path: str, duration: float, mood_info: dict) -> str:
    """
    Synthesizes a harmonically tuned, cinematic background music track tailored to the
    Gemini mood analysis (ambient drone + rhythmic pulse + melodic pad).
    """
    sample_rate = 44100
    bpm = int(mood_info.get("tempo_bpm", 90))
    beat_duration = 60.0 / bpm
    total_samples = int(duration * sample_rate)

    # Base chord frequencies based on style
    # D minor / cinematic: D3 (146.83), F3 (174.61), A3 (220.0), C4 (261.63)
    # A minor / mystery: A2 (110.0), C3 (130.81), E3 (164.81), G3 (196.0)
    chords = [
        [110.0, 164.81, 220.0],  # A minor
        [130.81, 196.0, 261.63], # C major
        [146.83, 220.0, 293.66], # D minor
        [98.0, 146.83, 196.0],   # G major
    ]

    samples = []
    for i in range(total_samples):
        t = i / sample_rate
        # Bar progression: each chord lasts 4 beats
        bar_index = int(t / (beat_duration * 4)) % len(chords)
        active_chord = chords[bar_index]

        # 1. Warm pad synth (sum of sines with gentle detuning and chorus)
        pad = 0.0
        for freq in active_chord:
            pad += math.sin(2.0 * math.pi * freq * t)
            pad += 0.5 * math.sin(2.0 * math.pi * (freq * 1.003) * t)

        pad *= 0.15

        # 2. Gentle rhythmic sub-pulse on each beat
        beat_t = (t % beat_duration) / beat_duration
        pulse_env = math.exp(-6.0 * beat_t)
        pulse = math.sin(2.0 * math.pi * 55.0 * t) * pulse_env * 0.25

        # 3. Ambient shimmer
        shimmer = math.sin(2.0 * math.pi * (active_chord[2] * 2.0) * t) * 0.05

        # Master mix with smooth fade in and fade out
        fade_in = min(1.0, t / 3.0)
        fade_out = min(1.0, (duration - t) / 3.0)
        master_env = fade_in * fade_out

        sample = (pad + pulse + shimmer) * master_env * 0.8
        samples.append(sample)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with wave.open(output_path, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        packed = bytearray()
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            packed.extend(struct.pack("<h", int(clamped * 32767.0)))
        wav_file.writeframes(packed)

    return output_path

class GeminiMusicError(Exception):
    pass

def get_api_key() -> str:
    configured_key = str(config.gemini.get("api_key", "") or "").strip()
    return configured_key or os.getenv("GEMINI_API_KEY", "").strip()

def is_enabled() -> bool:
    return True

def validate_generation_access():
    pass


def generate_bgm(video_path: str, output_path: str, video_duration: float, prompt: str = "") -> str:
    """
    Standard video music provider interface invoked by task.py.
    """
    try:
        mood_info = {
            "mood": "cinematic ambient",
            "tempo_bpm": 95,
            "style": "ambient",
            "intensity": "medium"
        }
        if prompt:
            mood_info = analyze_music_mood_with_gemini(prompt, prompt)
        synthesize_procedural_gemini_bgm(output_path, video_duration, mood_info)
        return output_path
    except Exception as exc:
        logger.exception(f"Gemini BGM generation failed: {exc}")
        raise GeminiMusicError(str(exc)) from exc

def generate_gemini_bgm_track(subject: str, script: str, duration: float) -> str:
    """
    Main entrypoint: analyzes script with Gemini and produces matching BGM track.
    """
    bgm_dir = utils.storage_dir("gemini_bgm", create=True)
    output_wav = os.path.join(bgm_dir, f"gemini_bgm_{abs(hash(subject + script[:50]))}.wav")

    mood_info = analyze_music_mood_with_gemini(subject, script)
    logger.info(f"Gemini BGM composition mood: {mood_info}")

    synthesize_procedural_gemini_bgm(output_wav, duration, mood_info)
    return output_wav

