import math
import os
import struct
import wave
from loguru import logger
from app.utils import utils

def _generate_wav(file_path: str, samples: list[float], sample_rate: int = 44100):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with wave.open(file_path, "wb") as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        packed_frames = bytearray()
        for s in samples:
            # Clamp between -1.0 and 1.0
            clamped = max(-1.0, min(1.0, s))
            sample_val = int(clamped * 32767.0)
            packed_frames.extend(struct.pack("<h", sample_val))
        wav_file.writeframes(packed_frames)

def create_whoosh_sfx(output_path: str, duration: float = 0.8, sample_rate: int = 44100) -> str:
    """Creates a smooth cinematic whoosh transition sound effect."""
    num_samples = int(duration * sample_rate)
    samples = []
    # Bandpass filtered noise sweep
    import random
    rng = random.Random(42)
    last_noise = 0.0
    for i in range(num_samples):
        t = i / num_samples
        # Envelope: parabolic fade in and out
        envelope = math.sin(math.pi * t) ** 2
        # Frequency rises then falls
        freq = 150.0 + 900.0 * math.sin(math.pi * t)
        # Noise component
        white = rng.uniform(-1.0, 1.0)
        # Lowpass filter noise
        last_noise = last_noise + 0.15 * (white - last_noise)
        # Sine component
        sine = math.sin(2.0 * math.pi * freq * (i / sample_rate))
        sample = (0.6 * sine + 0.4 * last_noise) * envelope
        samples.append(sample * 0.7)
    _generate_wav(output_path, samples, sample_rate)
    return output_path

def create_impact_sfx(output_path: str, duration: float = 1.2, sample_rate: int = 44100) -> str:
    """Creates a deep cinematic sub-bass impact / boom sound effect."""
    num_samples = int(duration * sample_rate)
    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        # Fast exponential decay
        envelope = math.exp(-3.5 * t)
        # Sub-bass pitch drop from 120Hz down to 35Hz
        freq = 35.0 + 85.0 * math.exp(-8.0 * t)
        sine = math.sin(2.0 * math.pi * freq * t)
        # Subtle harmonic
        harmonic = 0.3 * math.sin(4.0 * math.pi * freq * t)
        sample = (sine + harmonic) * envelope
        samples.append(sample * 0.8)
    _generate_wav(output_path, samples, sample_rate)
    return output_path

def create_riser_sfx(output_path: str, duration: float = 1.5, sample_rate: int = 44100) -> str:
    """Creates an atmospheric tension riser effect."""
    num_samples = int(duration * sample_rate)
    samples = []
    for i in range(num_samples):
        t = i / num_samples
        # Exponential swell
        envelope = (t ** 2.2)
        # Pitch rises from 80Hz to 480Hz
        freq = 80.0 + 400.0 * (t ** 1.8)
        sine = math.sin(2.0 * math.pi * freq * (i / sample_rate))
        sample = sine * envelope
        samples.append(sample * 0.6)
    _generate_wav(output_path, samples, sample_rate)
    return output_path

def get_preset_sfx_dir() -> str:
    sfx_dir = utils.storage_dir("sfx", create=True)
    whoosh_file = os.path.join(sfx_dir, "transition_whoosh.wav")
    impact_file = os.path.join(sfx_dir, "cinematic_impact.wav")
    riser_file = os.path.join(sfx_dir, "tension_riser.wav")

    if not os.path.exists(whoosh_file):
        create_whoosh_sfx(whoosh_file)
    if not os.path.exists(impact_file):
        create_impact_sfx(impact_file)
    if not os.path.exists(riser_file):
        create_riser_sfx(riser_file)

    return sfx_dir

def get_transition_sfx_clips(clip_durations: list[float], sfx_volume: float = 0.3) -> list[dict]:
    """
    Computes timestamps for sound effects at scene transitions.
    Returns list of dicts: [{'file': path, 'start_time': t, 'volume': sfx_volume}]
    """
    if not clip_durations or len(clip_durations) < 2:
        return []

    sfx_dir = get_preset_sfx_dir()
    whoosh_path = os.path.join(sfx_dir, "transition_whoosh.wav")
    impact_path = os.path.join(sfx_dir, "cinematic_impact.wav")

    transitions = []
    current_time = 0.0

    for idx, duration in enumerate(clip_durations[:-1]):
        current_time += duration
        # Place whoosh just before the cut (0.3s lead-in)
        whoosh_start = max(0.0, current_time - 0.3)
        transitions.append({
            "file": whoosh_path,
            "start_time": whoosh_start,
            "volume": sfx_volume
        })
        # Add subtle impact on the first major transition or every 3rd cut
        if idx == 0 or idx % 3 == 0:
            transitions.append({
                "file": impact_path,
                "start_time": current_time,
                "volume": sfx_volume * 0.7
            })

    return transitions
