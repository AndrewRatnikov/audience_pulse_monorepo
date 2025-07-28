from urllib.parse import urlparse
from .youtube_client import get_youtube_data
from ..logger import logger

def analyze_link(link: str):
    """
    Parses the provided link to identify the social media platform.
    """
    hostname = urlparse(link).hostname
    
    if hostname is None:
        logger.info(f"It's an unknown link - {link}")
        return

    if "youtube.com" in hostname or "youtu.be" in hostname:
        logger.info(f"It's a YouTube link - {link}")
        return get_youtube_data(link)
    elif "facebook.com" in hostname:
        logger.info(f"It's a Facebook link - {link}")
    elif "instagram.com" in hostname:
        logger.info(f"It's an Instagram link - {link}")
    else:
        logger.info(f"It's an unknown link - {link}")
