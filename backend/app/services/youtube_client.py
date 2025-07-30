from urllib.parse import urlparse, parse_qs
from ..logger import logger


def get_youtube_data(url: str):
    """
    Parses a YouTube URL to extract video ID or channel identifier.
    """
    logger.info(f"Parsing YouTube URL: {url}")
    
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname
    path = parsed_url.path
    
    if not hostname:
        logger.warning(f"Invalid URL provided: {url}")
        return {"error": "Invalid URL", "url": url}

    # Handle standard youtube.com URLs
    if 'youtube.com' in hostname:
        if path.startswith('/watch'):
            query_params = parse_qs(parsed_url.query)
            if 'v' in query_params:
                video_id = query_params['v'][0]
                logger.info(f"Found YouTube video ID: {video_id}")
                # Placeholder for API call using video_id
                return {"video_id": video_id, "url_type": "video"}
        elif path.startswith('/@'):
            channel_name = path[2:]
            logger.info(f"Found YouTube channel name: {channel_name}")
            # Placeholder for API call using channel_name
            return {"channel_name": channel_name, "url_type": "channel"}
        elif path.startswith('/channel/'):
            channel_id = path.split('/')[2]
            logger.info(f"Found YouTube channel ID: {channel_id}")
            # Placeholder for API call using channel_id
            return {"channel_id": channel_id, "url_type": "channel_id"}

    # Handle shortened youtu.be URLs
    elif 'youtu.be' in hostname:
        video_id = path[1:]  # The video ID is the path itself
        logger.info(f"Found YouTube video ID from youtu.be link: {video_id}")
        # Placeholder for API call using video_id
        return {"video_id": video_id, "url_type": "video"}

    logger.warning(f"Could not parse a recognized format from YouTube URL: {url}")
    return {"error": "Unrecognized YouTube URL format", "url": url}