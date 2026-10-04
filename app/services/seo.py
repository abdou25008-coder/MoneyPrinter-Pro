import json
import re
from loguru import logger
from app.services import llm
from app.config import config

def generate_social_seo(
    video_subject: str,
    video_script: str = "",
    platform: str = "all",
    language: str = "ar",
) -> dict:
    """
    Generates high-converting, engaging SEO titles, descriptions, and hashtags
    with emojis and strong hooks tailored for YouTube Shorts, TikTok, Instagram Reels, and Facebook.
    """
    prompt = f"""
أنت خبير محترف في تحسين محركات البحث وصناعة المحتوى الفيروسي (Viral SEO & Social Media Growth Specialist).
المطلوب إعداد حزمة نشر احترافية متكاملة لفيديو بالمواصفات التالية:

موضوع الفيديو: {video_subject}
نص/سيناريو الفيديو: {video_script[:1500] if video_script else video_subject}

يرجى توليد نصوص النشر باللغة العربية بأسلوب جذاب للغاية ومثير للفضول، مع استخدام الإيموجيات الذكية والهاشتاجات الرائجة، مقسمة لكل منصة من المنصات التالية بتنسيق JSON حصراً:

{{
    "youtube": {{
        "title": "عنوان جذاب جداً مع هوك قوي وإيموجي يناسب YouTube Shorts (أقل من 70 حرف)",
        "description": "وصف شيق ومثير يلخص محتوى الفيديو ويدعو للاشتراك والمشاهدة مع نقاط تفاعلية",
        "hashtags": "#هاشتاج1 #هاشتاج2 #Shorts #YouTubeShorts #شورتس #اكسبلور"
    }},
    "tiktok": {{
        "title": "كابشن فيروزي سريع ومثير للتفاعل مع هوك قوي وإيموجيات",
        "description": "وصف قصير وتفاعلي يطرح سؤالاً يثير الجدل والتعليقات",
        "hashtags": "#fyp #foryou #viral #تيك_توك #ترند #اكسبلور #معلومات"
    }},
    "instagram": {{
        "title": "عنوان أنيق وجذاب للـ Reels",
        "description": "كابشن تفصيلي جذاب ومنسق بعناية بنقاط وإيموجيات مع دعوة للمتابعة وحفظ الفيديو (Save this reel)",
        "hashtags": "#reels #explore #instagram #ريلز #اكسبلور #معرفة"
    }},
    "facebook": {{
        "title": "عنوان شيق ومثير للاهتمام للفيسبوك",
        "description": "منشور مفصل ومحفز للمشاركة والنقاش وطرح الآراء في التعليقات",
        "hashtags": "#فيسبوك #فيديو #معلومات #ثقافة #شاهد"
    }},
    "all_in_one": {{
        "title": "عنوان شامل فائق الجاذبية لجميع المنصات",
        "description": "وصف عام شامل ومرن يناسب النشر التلقائي الموحد",
        "hashtags": "#shorts #reels #tiktok #viral #اكسبلور #ترند"
    }}
}}

تنبيه هام: أرجع كود JSON فقط بدون أي مقدمات أو شروحات إضافية.
"""

    try:
        response_text = llm._generate_response(prompt=prompt)
        # Clean potential markdown fences
        clean_text = re.sub(r"^```json\s*", "", response_text.strip(), flags=re.MULTILINE)
        clean_text = re.sub(r"^```\s*$", "", clean_text.strip(), flags=re.MULTILINE)
        clean_text = clean_text.strip()
        
        # Try finding the json object inside response
        match = re.search(r"\{.*\}", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(0)
            
        data = json.loads(clean_text)
        return data
    except Exception as exc:
        logger.warning(f"Failed to generate social SEO metadata via LLM: {exc}")
        # Fallback default values
        clean_subj = video_subject.strip() or "فيديو وثائقي مميز"
        return {
            "youtube": {
                "title": f"🔥 سر خطير ومثير: {clean_subj} | وثائقي لا يصدق!",
                "description": f"اكتشف الحقائق المدهشة والأسرار الخفية حول {clean_subj}. لا تنسَ الاشتراك في القناة وتفعيل الجرس للمزيد من المغامرات الوثائقية المثيرة! 🔔✨",
                "hashtags": f"#Shorts #YouTubeShorts #وثائقي #معلومات #اكسبلور #{clean_subj.replace(' ', '_')[:20]}"
            },
            "tiktok": {
                "title": f"😱 لن تصدق ما ستراه عن {clean_subj}! تفاصيل لأول مرة",
                "description": f"هل كنت تعرف هذه الحقيقة الصادمة عن {clean_subj}؟ شاركنا رأيك في التعليقات! 👇🔥",
                "hashtags": f"#fyp #foryou #viral #تيك_توك #ترند #اكسبلور #{clean_subj.replace(' ', '_')[:20]}"
            },
            "instagram": {
                "title": f"✨ رحلة وثائقية غامضة: {clean_subj}",
                "description": f"حقائق مثيرة وغامضة تكشف لأول مرة عن {clean_subj}.\n\n📌 احفظ الريلز للرجوع إليه لاحقاً وشاركه مع أصدقائك!\n🔔 تابعنا للمزيد من الاكتشافات اليومية.",
                "hashtags": f"#reels #explore #instagram #ريلز #اكسبلور #معرفة #{clean_subj.replace(' ', '_')[:20]}"
            },
            "facebook": {
                "title": f"🌍 حقائق مذهلة عن {clean_subj} ستغير نظرتك تماماً!",
                "description": f"شاهد هذا التقرير الوثائقي المثير حول {clean_subj}. هل كنت على علم بهذه التفاصيل من قبل؟ أخبرنا بتجربتك ورأيك في التعليقات.",
                "hashtags": f"#فيسبوك #فيديو #معلومات #ثقافة #شاهد #{clean_subj.replace(' ', '_')[:20]}"
            },
            "all_in_one": {
                "title": f"🔥 حقائق مذهلة وغامضة: {clean_subj}",
                "description": f"استكشف الأسرار والحقائق المثيرة حول {clean_subj}. تابعنا واشترك لمشاهدة أحدث الفيديوهات الوثائقية الشيقة! ✨🔔",
                "hashtags": f"#shorts #reels #tiktok #viral #اكسبلور #ترند #{clean_subj.replace(' ', '_')[:20]}"
            }
        }
