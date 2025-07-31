from urllib.parse import urlparse
from ..config import settings
from .youtube_client import YouTubeFetcher
from ..logger import logger

def analyze_link(link: str):
    """
    Parses the provided link to identify the social media platform and fetches data.
    """
    hostname = urlparse(link).hostname
    path = urlparse(link).path

    if not hostname:
        logger.info(f"It's an unknown link - {link}")
        return {"error": "Invalid link"}

    if "youtube.com" in hostname or "youtu.be" in hostname:
        logger.info(f"It's a YouTube link - {link}")
        if not settings.YOUTUBE_API_KEY:
            logger.error("YouTube API Key is not set.")
            return {"error": "YouTube API Key is not configured."}
        
        fetcher = YouTubeFetcher(api_key=settings.YOUTUBE_API_KEY)
        
        # Determine if it's a video or channel link
        if 'watch' in path or 'youtu.be' in hostname:
            return fetcher.get_video_data(link)
        else:
            return fetcher.get_channel_data(link)

    elif "facebook.com" in hostname:
        logger.info(f"It's a Facebook link - {link}")
        return {"status": "Facebook analysis not yet implemented."}
    
    elif "instagram.com" in hostname:
        logger.info(f"It's an Instagram link - {link}")
        return {"status": "Instagram analysis not yet implemented."}
    
    else:
        logger.info(f"It's an unknown link - {link}")
        return {"error": "Unknown or unsupported link type"}