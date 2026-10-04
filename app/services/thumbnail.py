"""
Thumbnail and Cover Art Service
It provides creation, processing, and output of video covers.
"""
import os
import shutil
from typing import Optional
from PIL import Image
from loguru import logger
from app.config import config
from app.services import free_image, llm
from app.utils import utils

def generate_thumbnail_prompt(video_subject: str, video_script: str = "") -> str:
    subject_text = (video_subject or "").strip()
    script_snippet = (video_script or "").strip()[:500]

    system_instruction = (
        "You are an expert YouTube/video thumbnail designer for National Geographic and BBC documentaries. "
        "Create a single-paragraph English prompt for a cinematic, photorealistic, 8k resolution thumbnail. "
        "Focus on: dramatic lighting, vibrant contrast, hyper-detailed focal subject, epic sense of scale, and mystery. "
        "Output ONLY the image prompt itself without any preamble, quotes, or conversational text."
    )

    user_prompt = f"Video Subject: {subject_text}\nContext Snippet: {script_snippet}"

    try:
        generated = llm.generate_response(
            prompt=user_prompt,
            system_instruction=system_instruction,
            temperature=0.7,
        )
        if generated and len(generated.strip()) > 20:
            clean = generated.strip().replace('"', '').replace('\n', ' ')
            logger.info(f"Generated AI thumbnail prompt: {clean[:80]}...")
            return clean
    except Exception as exc:
        logger.warning(f"Failed to generate thumbnail prompt via LLM ({exc}), using fallback template")

    return (
        f"Cinematic National Geographic documentary cover art, 8k resolution, ultra-realistic, "
        f"dramatic volumetric lighting, vivid colors, depth of field, epic composition of {subject_text or 'mysterious discovery'}"
    )

def create_thumbnail(
    mode: str = "prompt",
    video_subject: str = "",
    video_script: str = "",
    custom_prompt: str = "",
    uploaded_file_bytes: Optional[bytes] = None,
    aspect_ratio: str = "16:9",
    output_dir: str = "",
    provider: str = "pollinations",
) -> str:
    if not output_dir:
        output_dir = utils.storage_dir("thumbnails", create=True)
    os.makedirs(output_dir, exist_ok=True)

    final_thumb_path = os.path.join(output_dir, "thumbnail.jpg")

    if "9:16" in aspect_ratio or "portrait" in aspect_ratio.lower():
        target_w, target_h = 1080, 1920
        aspect_str = "9:16"
    else:
        target_w, target_h = 1920, 1080
        aspect_str = "16:9"

    temp_image_path = ""

    try:
        if mode == "upload" and uploaded_file_bytes:
            with open(final_thumb_path, "wb") as f:
                f.write(uploaded_file_bytes)
            temp_image_path = final_thumb_path
        elif mode == "prompt" and custom_prompt.strip():
            logger.info(f"Generating thumbnail from custom prompt: {custom_prompt[:60]}...")
            temp_image_path = free_image.generate_image_by_provider(
                provider=provider,
                prompt=custom_prompt.strip(),
                aspect=aspect_str,
            )
        elif mode in ("auto", "prompt"):
            prompt = generate_thumbnail_prompt(video_subject, video_script)
            logger.info(f"Generating thumbnail via auto prompt: {prompt[:60]}...")
            temp_image_path = free_image.generate_image_by_provider(
                provider=provider,
                prompt=prompt,
                aspect=aspect_str,
            )
        else:
            return ""

        if temp_image_path and os.path.exists(temp_image_path):
            with Image.open(temp_image_path) as img:
                img_rgb = img.convert("RGB")
                if img_rgb.size != (target_w, target_h):
                    img_resized = img_rgb.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    img_resized.save(final_thumb_path, "JPEG", quality=95)
                else:
                    img_rgb.save(final_thumb_path, "JPEG", quality=95)
            logger.success(f"Thumbnail created successfully: {final_thumb_path}")
            return final_thumb_path
    except Exception as exc:
        logger.error(f"Error creating thumbnail: {exc}")

    return ""
