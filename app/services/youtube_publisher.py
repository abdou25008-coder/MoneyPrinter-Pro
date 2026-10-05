import os
import json
from typing import Optional, Dict, Any, List
from loguru import logger
from app.config import config
from app.utils import utils

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/youtube",
]

class YouTubePublishService:
    @property
    def client_id(self) -> str:
        return config.app.get("youtube_client_id", "") or os.environ.get("YOUTUBE_CLIENT_ID", "")

    @property
    def client_secret(self) -> str:
        return config.app.get("youtube_client_secret", "") or os.environ.get("YOUTUBE_CLIENT_SECRET", "")

    @property
    def enabled(self) -> bool:
        return bool(config.app.get("youtube_direct_enabled", False))

    def get_credentials_path(self) -> str:
        storage_dir = utils.storage_dir("youtube", create=True)
        return os.path.join(storage_dir, "token.json")

    def get_client_config(self) -> dict:
        return {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [
                    "http://localhost:8501/",
                    "http://127.0.0.1:8501/",
                    "http://localhost:8080/",
                    "urn:ietf:wg:oauth:2.0:oob",
                ],
            }
        }

    def is_authenticated(self) -> bool:
        token_path = self.get_credentials_path()
        if not os.path.exists(token_path):
            return False
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if creds and creds.valid:
                return True
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, "w", encoding="utf-8") as f:
                    f.write(creds.to_json())
                return True
        except Exception as exc:
            logger.debug(f"YouTube credentials validation failed: {exc}")
        return False

    def get_channel_info(self) -> Dict[str, Any]:
        if not self.is_authenticated():
            return {"authenticated": False, "channel_name": "", "channel_id": ""}
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            token_path = self.get_credentials_path()
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            youtube = build("youtube", "v3", credentials=creds)
            resp = youtube.channels().list(part="snippet,contentDetails,statistics", mine=True).execute()
            items = resp.get("items", [])
            if items:
                snippet = items[0].get("snippet", {})
                return {
                    "authenticated": True,
                    "channel_name": snippet.get("title", "YouTube Channel"),
                    "channel_id": items[0].get("id", ""),
                    "custom_url": snippet.get("customUrl", ""),
                    "avatar": snippet.get("thumbnails", {}).get("default", {}).get("url", ""),
                }
        except Exception as exc:
            logger.warning(f"Failed to fetch YouTube channel info: {exc}")
        return {"authenticated": False, "error": "فشل جلب معلومات القناة"}

    def get_auth_url(self) -> str:
        from google_auth_oauthlib.flow import Flow
        client_config = self.get_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",
        )
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline", include_granted_scopes="true")
        return auth_url

    def exchange_code_for_token(self, code: str) -> bool:
        try:
            from google_auth_oauthlib.flow import Flow
            client_config = self.get_client_config()
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri="urn:ietf:wg:oauth:2.0:oob",
            )
            flow.fetch_token(code=code.strip())
            creds = flow.credentials
            token_path = self.get_credentials_path()
            with open(token_path, "w", encoding="utf-8") as f:
                f.write(creds.to_json())
            logger.info("YouTube direct credentials saved successfully.")
            return True
        except Exception as exc:
            logger.error(f"Failed to exchange YouTube auth code: {exc}")
            return False

    def upload_video(
        self,
        video_path: str,
        title: str = "",
        description: str = "",
        tags: Optional[List[str]] = None,
        privacy_status: str = "public",
        made_for_kids: bool = False,
    ) -> Dict[str, Any]:
        if not os.path.exists(video_path):
            return {"success": False, "error": f"الملف غير موجود: {video_path}"}
        if not self.is_authenticated():
            return {"success": False, "error": "لم يتم توثيق الاتصال بقناة يوتيوب"}

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            token_path = self.get_credentials_path()
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": (title or "YouTube Shorts Video")[:100],
                    "description": (description or "#Shorts")[:5000],
                    "tags": tags or ["Shorts", "YouTubeShorts"],
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": privacy_status or "public",
                    "selfDeclaredMadeForKids": made_for_kids,
                },
            }

            media = MediaFileUpload(
                video_path,
                chunksize=1024 * 1024 * 4,
                resumable=True,
                mimetype="video/mp4",
            )

            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"YouTube direct upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id", "")
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"YouTube video uploaded successfully: {video_url}")
            return {
                "success": True,
                "video_id": video_id,
                "video_url": video_url,
                "response": response,
            }
        except Exception as exc:
            logger.error(f"YouTube direct upload failed: {exc}")
            return {"success": False, "error": str(exc)}

youtube_service = YouTubePublishService()
