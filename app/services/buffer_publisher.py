"""
Buffer API integration for automatic social media publishing and cross-posting.
Supports Instagram, TikTok, YouTube Shorts, Facebook, Twitter/X, and LinkedIn.
Docs: https://buffer.com/developers/api
"""
import os
from typing import Optional, List
import requests
from loguru import logger
from app.config import config

class BufferPublishService:
    API_BASE = "https://api.bufferapp.com/1"

    @property
    def access_token(self) -> str:
        return config.app.get("buffer_access_token", "") or os.environ.get("BUFFER_ACCESS_TOKEN", "")

    @property
    def enabled(self) -> bool:
        return bool(config.app.get("buffer_enabled", False))

    @property
    def default_profile_ids(self) -> list:
        val = config.app.get("buffer_profile_ids", [])
        if isinstance(val, str):
            return [p.strip() for p in val.split(",") if p.strip()]
        return val or []

    def is_configured(self) -> bool:
        return bool(self.access_token)

    def get_profiles(self) -> List[dict]:
        """Fetches all connected social media channels/profiles from Buffer."""
        if not self.is_configured():
            logger.warning("Buffer access token not set.")
            return []

        url = f"{self.API_BASE}/profiles.json"
        params = {"access_token": self.access_token}
        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                profiles = []
                for p in data:
                    profiles.append({
                        "id": p.get("id"),
                        "service": p.get("service"),       # instagram, facebook, twitter, etc.
                        "formatted_username": p.get("formatted_username", ""),
                        "avatar": p.get("avatar", ""),
                        "service_type": p.get("service_type", "")
                    })
                return profiles
            else:
                logger.error(f"Buffer API error: {resp.status_code} - {resp.text}")
                return []
        except Exception as exc:
            logger.error(f"Failed to connect to Buffer API: {exc}")
            return []

    def publish_video(
        self,
        video_url: str,
        text: str,
        profile_ids: Optional[List[str]] = None,
        now: bool = False,
    ) -> dict:
        """
        Creates an update in Buffer for the selected profiles.
        """
        if not self.is_configured():
            return {"success": False, "error": "Buffer is not configured"}

        targets = profile_ids or self.default_profile_ids
        if not targets:
            return {"success": False, "error": "No Buffer profiles selected"}

        url = f"{self.API_BASE}/updates/create.json"
        params = {"access_token": self.access_token}

        payload = {
            "text": text,
            "profile_ids[]": targets,
            "now": "true" if now else "false",
        }

        if video_url:
            payload["media[video]"] = video_url

        try:
            resp = requests.post(url, params=params, data=payload, timeout=30)
            if resp.status_code == 200:
                res = resp.json()
                logger.info(f"Buffer post created successfully: {res.get('updates', [])}")
                return {"success": True, "data": res}
            else:
                logger.error(f"Buffer publish failed: {resp.status_code} - {resp.text}")
                return {"success": False, "error": resp.text}
        except Exception as exc:
            logger.error(f"Buffer request exception: {exc}")
            return {"success": False, "error": str(exc)}

buffer_service = BufferPublishService()
