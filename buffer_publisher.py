"""
Buffer API integration for automatic social media publishing and cross-posting.
Supports Instagram, TikTok, YouTube Shorts, Facebook, Twitter/X, LinkedIn, and Threads.
Supports both modern Buffer GraphQL API (api.buffer.com) and legacy REST API (api.bufferapp.com/1).
Docs: https://buffer.com/developers/api
"""
import os
from typing import Optional, List, Dict, Any
import requests
from loguru import logger
from app.config import config


SERVICE_DISPLAY_NAMES = {
    "instagram": "📸 Instagram",
    "tiktok": "🎵 TikTok",
    "youtube": "▶️ YouTube Shorts",
    "facebook": "📘 Facebook",
    "linkedin": "💼 LinkedIn",
    "twitter": "🐦 X (Twitter)",
    "x": "🐦 X (Twitter)",
    "pinterest": "📌 Pinterest",
    "threads": "🧵 Threads",
    "mastodon": "🐘 Mastodon",
    "bluesky": "🦋 Bluesky",
}


class BufferPublishService:
    GRAPHQL_API_URL = "https://api.buffer.com"
    REST_API_BASE = "https://api.bufferapp.com/1"

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

    def get_profiles(self, token: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Fetches all connected social media channels/profiles from Buffer.
        Tries modern GraphQL API first, then falls back to legacy REST API.
        """
        active_token = (token or self.access_token).strip()
        if not active_token:
            logger.warning("Buffer access token not set.")
            return []

        # 1. Attempt GraphQL API
        graphql_profiles = self._fetch_profiles_graphql(active_token)
        if graphql_profiles:
            logger.info(f"Retrieved {len(graphql_profiles)} Buffer channels via GraphQL API.")
            return graphql_profiles

        # 2. Fallback to Legacy REST API
        rest_profiles = self._fetch_profiles_rest(active_token)
        if rest_profiles:
            logger.info(f"Retrieved {len(rest_profiles)} Buffer profiles via REST API.")
            return rest_profiles

        return []

    def _fetch_profiles_graphql(self, token: str) -> List[Dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "MoneyPrinterPro/2.0",
        }

        # Step 1: Query Organizations
        org_query = """
        query GetOrganizations {
            account {
                organizations {
                    id
                    name
                }
            }
        }
        """
        try:
            resp = requests.post(
                self.GRAPHQL_API_URL,
                json={"query": org_query},
                headers=headers,
                timeout=12,
            )
            if resp.status_code != 200:
                logger.debug(f"Buffer GraphQL organizations query HTTP {resp.status_code}: {resp.text}")
                return []

            res_json = resp.json()
            if "errors" in res_json:
                logger.debug(f"Buffer GraphQL organizations errors: {res_json.get('errors')}")
                return []

            orgs = (
                res_json.get("data", {})
                .get("account", {})
                .get("organizations", [])
            )
            if not orgs:
                return []

            profiles = []
            channels_query = """
            query GetChannels($orgId: String!) {
                channels(input: { organizationId: $orgId }) {
                    id
                    name
                    service
                    avatarUrl
                }
            }
            """

            for org in orgs:
                org_id = org.get("id")
                if not org_id:
                    continue
                c_resp = requests.post(
                    self.GRAPHQL_API_URL,
                    json={"query": channels_query, "variables": {"orgId": org_id}},
                    headers=headers,
                    timeout=12,
                )
                if c_resp.status_code == 200:
                    c_data = c_resp.json()
                    channels = c_data.get("data", {}).get("channels", [])
                    for ch in channels:
                        service_code = str(ch.get("service", "")).lower()
                        profiles.append({
                            "id": ch.get("id"),
                            "service": service_code,
                            "service_name": SERVICE_DISPLAY_NAMES.get(service_code, service_code.capitalize()),
                            "formatted_username": ch.get("name", "Unnamed Channel"),
                            "avatar": ch.get("avatarUrl", ""),
                            "organization": org.get("name", ""),
                        })
            return profiles
        except Exception as exc:
            logger.debug(f"Buffer GraphQL fetch exception: {exc}")
            return []

    def _fetch_profiles_rest(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.REST_API_BASE}/profiles.json"
        params = {"access_token": token}
        try:
            resp = requests.get(url, params=params, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                if not isinstance(data, list):
                    return []
                profiles = []
                for p in data:
                    service_code = str(p.get("service", "")).lower()
                    profiles.append({
                        "id": p.get("id"),
                        "service": service_code,
                        "service_name": SERVICE_DISPLAY_NAMES.get(service_code, service_code.capitalize()),
                        "formatted_username": p.get("formatted_username", p.get("service_username", "")),
                        "avatar": p.get("avatar", ""),
                        "service_type": p.get("service_type", ""),
                    })
                return profiles
            else:
                logger.debug(f"Buffer REST profiles error: {resp.status_code} - {resp.text}")
                return []
        except Exception as exc:
            logger.debug(f"Buffer REST fetch exception: {exc}")
            return []

    def test_connection(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Validates token and returns connected channels/profiles."""
        active_token = (token or self.access_token).strip()
        if not active_token:
            return {"success": False, "error": "رمز الوصول (Access Token) غير محدد"}

        try:
            profiles = self.get_profiles(active_token)
            if profiles:
                return {
                    "success": True,
                    "count": len(profiles),
                    "profiles": profiles,
                    "message": f"تم الاتصال بنجاح! تم العثور على {len(profiles)} قناة/صفحة مرتبطة.",
                }
            else:
                return {
                    "success": False,
                    "profiles": [],
                    "error": "لم يتم العثور على أي قنوات مرتبطة بحساب Buffer هذا. تأكد من صحة الرمز ومن ربط قنوات التواصل في حسابك على Buffer.",
                }
        except Exception as exc:
            return {"success": False, "error": f"خطأ أثناء الاتصال بـ Buffer: {str(exc)}"}

    def publish_video(
        self,
        video_path: Optional[str] = None,
        video_url: Optional[str] = None,
        text: str = "",
        profile_ids: Optional[List[str]] = None,
        now: bool = False,
    ) -> Dict[str, Any]:
        """
        Creates an update/post in Buffer for the selected profiles.
        """
        if not self.is_configured():
            return {"success": False, "error": "لم يتم إعداد مفتاح منصة Buffer"}

        targets = profile_ids or self.default_profile_ids
        if not targets:
            return {"success": False, "error": "لم يتم تحديد أي صفحات أو قنوات لنشر الفيديو"}

        media_url = video_url or ""
        # If running locally or on server where video_path exists, note that Buffer requires public HTTP(S) URL
        if not media_url and video_path and (str(video_path).startswith("http://") or str(video_path).startswith("https://")):
            media_url = video_path

        # 1. Try GraphQL createPost for each channel
        graphql_results = self._publish_graphql(targets, text, media_url, now)
        if graphql_results.get("success"):
            return graphql_results

        # 2. Try REST API updates/create.json
        rest_results = self._publish_rest(targets, text, media_url, now)
        if rest_results.get("success"):
            return rest_results

        err = graphql_results.get("error") or rest_results.get("error") or "فشل في جدولة المنشور على Buffer"
        return {"success": False, "error": err}

    def _publish_graphql(self, targets: List[str], text: str, media_url: str, now: bool) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "User-Agent": "MoneyPrinterPro/2.0",
        }
        mutation = """
        mutation CreatePost($input: CreatePostInput!) {
            createPost(input: $input) {
                ... on PostActionSuccess {
                    post {
                        id
                        status
                    }
                }
                ... on MutationError {
                    message
                }
            }
        }
        """

        created_posts = []
        errors = []

        for channel_id in targets:
            input_payload: Dict[str, Any] = {
                "channelId": channel_id,
                "text": text,
                "schedulingType": "automatic",
                "mode": "shareNow" if now else "addToQueue",
            }
            if media_url:
                input_payload["assets"] = [{"type": "video", "url": media_url}]

            try:
                resp = requests.post(
                    self.GRAPHQL_API_URL,
                    json={"query": mutation, "variables": {"input": input_payload}},
                    headers=headers,
                    timeout=20,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    res_body = data.get("data", {}).get("createPost", {})
                    if "post" in res_body:
                        created_posts.append(res_body["post"])
                    elif "message" in res_body:
                        errors.append(f"Channel {channel_id}: {res_body['message']}")
                    elif "errors" in data:
                        errors.append(f"Channel {channel_id}: {str(data['errors'])}")
                else:
                    errors.append(f"Channel {channel_id}: HTTP {resp.status_code}")
            except Exception as exc:
                errors.append(f"Channel {channel_id}: {str(exc)}")

        if created_posts:
            logger.info(f"Buffer GraphQL published successfully to {len(created_posts)} channels.")
            return {"success": True, "created": created_posts, "errors": errors}
        return {"success": False, "error": "; ".join(errors) if errors else "GraphQL submission failed"}

    def _publish_rest(self, targets: List[str], text: str, media_url: str, now: bool) -> Dict[str, Any]:
        url = f"{self.REST_API_BASE}/updates/create.json"
        params = {"access_token": self.access_token}

        payload: Dict[str, Any] = {
            "text": text,
            "profile_ids[]": targets,
            "now": "true" if now else "false",
        }
        if media_url:
            payload["media[video]"] = media_url

        try:
            resp = requests.post(url, params=params, data=payload, timeout=25)
            if resp.status_code == 200:
                res = resp.json()
                logger.info(f"Buffer REST post created successfully: {res.get('updates', [])}")
                return {"success": True, "data": res}
            else:
                logger.error(f"Buffer REST publish failed: {resp.status_code} - {resp.text}")
                return {"success": False, "error": resp.text}
        except Exception as exc:
            logger.error(f"Buffer REST request exception: {exc}")
            return {"success": False, "error": str(exc)}


buffer_service = BufferPublishService()


def publish_video(
    video_path: Optional[str] = None,
    video_url: Optional[str] = None,
    text: str = "",
    profile_ids: Optional[List[str]] = None,
    now: bool = False,
) -> Dict[str, Any]:
    """Module-level helper to publish a video via Buffer."""
    return buffer_service.publish_video(
        video_path=video_path,
        video_url=video_url,
        text=text,
        profile_ids=profile_ids,
        now=now,
    )


def get_profiles(token: Optional[str] = None) -> List[Dict[str, Any]]:
    """Module-level helper to fetch profiles via Buffer."""
    return buffer_service.get_profiles(token=token)

