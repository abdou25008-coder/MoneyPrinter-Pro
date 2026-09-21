"""
AI Image generation integration supporting:
1. Pollinations.ai: Free, no key required, high quality FLUX / SDXL models.
2. Google Gemini Imagen: Uses existing Gemini API Key.
"""
import os
import urllib.parse
from typing import Optional
import requests
from loguru import logger
from app.config import config
from app.utils import utils

def generate_pollinations_image(prompt: str, width: int = 1080, height: int = 1920, seed: Optional[int] = None) -> str:
    """
    Generates a high-resolution image using Pollinations.ai (Free, unlimited FLUX engine).
    """
    image_dir = utils.storage_dir("ai_images", create=True)
    file_id = abs(hash(prompt + str(seed)))
    output_path = os.path.join(image_dir, f"pollinations_{file_id}.jpg")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path

    encoded_prompt = urllib.parse.quote(prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width={width}&height={height}&nologo=true"
    if seed is not None:
        url += f"&seed={seed}"

    logger.info(f"Generating Pollinations AI image for: {prompt[:60]}...")
    resp = requests.get(url, timeout=45)
    if resp.status_code == 200 and len(resp.content) > 1000:
        with open(output_path, "wb") as f:
            f.write(resp.content)
        return output_path
    else:
        raise RuntimeError(f"Pollinations AI failed with code {resp.status_code}")

def generate_gemini_imagen_image(prompt: str, aspect_ratio: str = "9:16") -> str:
    """
    Generates an image using Google's Imagen model via the existing Gemini API Key.
    """
    api_key = config.gemini.get("api_key") or os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("No Gemini API key, falling back to Pollinations AI")
        width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
        return generate_pollinations_image(prompt, width, height)

    image_dir = utils.storage_dir("ai_images", create=True)
    file_id = abs(hash(prompt + aspect_ratio))
    output_path = os.path.join(image_dir, f"gemini_imagen_{file_id}.jpg")

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        # Call Imagen 3
        result = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config=dict(
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                output_mime_type="image/jpeg",
            ),
        )
        for generated_image in result.generated_images:
            with open(output_path, "wb") as f:
                f.write(generated_image.image.image_bytes)
            return output_path
    except Exception as exc:
        logger.warning(f"Gemini Imagen failed ({exc}), falling back to Pollinations AI")
        width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
        return generate_pollinations_image(prompt, width, height)

    return ""

def generate_image_by_provider(provider: str, prompt: str, aspect: str = "9:16") -> str:
    if provider == "gemini_imagen":
        return generate_gemini_imagen_image(prompt, aspect_ratio=aspect)
    # Default to Pollinations (free, fast, no key needed)
    width, height = (1080, 1920) if aspect == "9:16" else (1920, 1080)
    return generate_pollinations_image(prompt, width=width, height=height)
