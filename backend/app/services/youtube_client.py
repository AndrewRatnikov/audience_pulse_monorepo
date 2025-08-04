from urllib.parse import urlparse, parse_qs
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from ..logger import logger

@dataclass
class FetchConfig:
    """Configuration class for YouTube fetcher settings."""
    max_videos: int = 50
    max_comments_per_video: int = 100
    popular_videos_count: int = 5
    least_popular_videos_count: int = 5
    retry_attempts: int = 5  # Increased from 3 to handle SSL issues
    retry_delay: float = 2.0  # Increased from 1.0 to give more time between retries
    enable_comments: bool = True
    enable_concurrent_fetching: bool = True
    max_workers: int = 5

class YouTubeFetcherError(Exception):
    """Custom exception for YouTube fetcher errors."""
    pass

def execute_with_timeout(func, timeout_seconds=30):
    """Execute a function with timeout using ThreadPoolExecutor."""
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func)
        try:
            return future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            future.cancel()
            raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")

class YouTubeFetcher:
    """Enhanced YouTube Data API v3 fetcher with improved error handling and performance."""

    def __init__(self, api_key: str, config: Optional[FetchConfig] = None, timeout: int = 15):
        """Initializes the YouTubeFetcher with an API key and configuration."""
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key  # Store API key for rebuilding client if needed
        self.timeout = timeout  # Reduced default timeout from 30 to 15 seconds
        
        # Build client with timeout configuration
        self.youtube = self._build_youtube_client()
        self.config = config or FetchConfig()
        self._cache = {}  # Simple in-memory cache

    def _build_youtube_client(self):
        """Build YouTube client with proper timeout configuration."""
        import socket
        
        # Set socket timeout globally for this client
        socket.setdefaulttimeout(self.timeout)
        
        try:
            client = build('youtube', 'v3', developerKey=self.api_key)
            return client
        finally:
            # Reset socket timeout to avoid affecting other parts of application
            socket.setdefaulttimeout(None)

    def _validate_url(self, url: str) -> bool:
        """Validates if the provided URL is a valid YouTube URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc in ['www.youtube.com', 'youtube.com', 'youtu.be']
        except Exception:
            return False

    def _retry_api_call(self, func, *args, **kwargs):
        """Retry mechanism for API calls with timeout and error handling."""
        for attempt in range(self.config.retry_attempts):
            try:
                # Execute API call with timeout
                def api_call():
                    request = func(*args, **kwargs)
                    return request.execute()
                
                result = execute_with_timeout(api_call, self.timeout)
                return result
                
            except (TimeoutError, FutureTimeoutError) as e:
                logger.warning(f"API call timed out on attempt {attempt + 1}: {e}")
                if attempt < self.config.retry_attempts - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logger.info(f"Retrying after {wait_time}s...")
                    time.sleep(wait_time)
                    
                    # Rebuild client on timeout
                    try:
                        logger.info("Rebuilding YouTube client due to timeout")
                        self.youtube = self._build_youtube_client()
                    except Exception as rebuild_error:
                        logger.warning(f"Failed to rebuild client: {rebuild_error}")
                    continue
                else:
                    raise YouTubeFetcherError(f"API call timed out after {self.config.retry_attempts} attempts")
                    
            except HttpError as e:
                if e.resp.status == 429:  # Rate limit exceeded
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logger.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}")
                    time.sleep(wait_time)
                    continue
                elif e.resp.status in [500, 502, 503, 504]:  # Server errors
                    if attempt < self.config.retry_attempts - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                raise
            except Exception as e:
                error_str = str(e)
                # Handle SSL and connection errors specifically
                if any(ssl_error in error_str.lower() for ssl_error in ['ssl', 'connection', 'timeout', 'record layer', 'read operation timed out']):
                    if attempt < self.config.retry_attempts - 1:
                        wait_time = self.config.retry_delay * (2 ** attempt)
                        logger.warning(f"Connection/SSL error on attempt {attempt + 1}: {error_str}")
                        logger.info(f"Retrying after {wait_time}s...")
                        time.sleep(wait_time)
                        
                        # Try to rebuild the YouTube client on SSL errors
                        try:
                            logger.info("Rebuilding YouTube client due to connection error")
                            self.youtube = self._build_youtube_client()
                        except Exception as rebuild_error:
                            logger.warning(f"Failed to rebuild client: {rebuild_error}")
                        
                        continue
                    else:
                        logger.error(f"Connection failed after {self.config.retry_attempts} attempts")
                        raise YouTubeFetcherError(f"Connection failed after {self.config.retry_attempts} attempts: {error_str}")
                else:
                    if attempt < self.config.retry_attempts - 1:
                        time.sleep(self.config.retry_delay)
                        continue
                raise
        raise YouTubeFetcherError(f"Failed after {self.config.retry_attempts} attempts")

    def _extract_video_id(self, video_url: str) -> Optional[str]:
        """Extracts video ID from various YouTube URL formats."""
        if not self._validate_url(video_url):
            return None
            
        parsed_url = urlparse(video_url)
        
        # Handle youtu.be format
        if parsed_url.netloc == 'youtu.be':
            return parsed_url.path.lstrip('/')
        
        # Handle youtube.com/watch format
        if 'watch' in parsed_url.path:
            return parse_qs(parsed_url.query).get('v', [None])[0]
        
        # Handle youtube.com/embed format
        if '/embed/' in parsed_url.path:
            return parsed_url.path.split('/embed/')[-1]
            
        return None

    def _extract_channel_id(self, youtube_link: str) -> Optional[str]:
        """Enhanced channel ID extraction with better error handling."""
        if not self._validate_url(youtube_link):
            logger.error(f"Invalid YouTube URL: {youtube_link}")
            return None
            
        # Check cache first
        cache_key = f"channel_id:{youtube_link}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        parsed_url = urlparse(youtube_link)
        path_parts = parsed_url.path.split('/')

        channel_id = None
        
        try:
            # Handle video URLs
            if 'watch' in parsed_url.path:
                video_id = self._extract_video_id(youtube_link)
                if video_id:
                    video_details = self._get_video_details([video_id])
                    if video_details:
                        channel_id = video_details[0].get('snippet', {}).get('channelId')
            
            # Handle direct channel URLs
            elif '/channel/' in parsed_url.path:
                channel_id = path_parts[-1]
            
            # Handle @ handles
            elif parsed_url.path.startswith('/@'):
                handle = parsed_url.path[2:]  # Remove the leading /@
                logger.info(f"Extracted handle: {handle}")
                channel_id = self._search_channel_by_handle(handle)
                
                # Additional fallback: try to construct channel URL and test it
                if not channel_id:
                    logger.info(f"Search failed, trying direct URL construction")
                    channel_id = self._try_direct_handle_resolution(handle)
            
            # Handle legacy formats (/c/, /user/)
            elif any(x in parsed_url.path for x in ['/c/', '/user/']):
                query = path_parts[-1]
                channel_id = self._search_channel_by_query(query)
                
        except Exception as e:
            logger.error(f"Error extracting channel ID from {youtube_link}: {e}")
            
        # Cache the result
        if channel_id:
            self._cache[cache_key] = channel_id
            logger.info(f"Successfully extracted channel ID: {channel_id}")
        else:
            logger.error(f"Failed to extract channel ID from {youtube_link}")
            
        return channel_id

    def test_api_connection(self) -> bool:
        """Test if the API connection is working properly."""
        try:
            # Try a simple API call to test connectivity
            response = self.youtube.search().list(
                q="test",
                type='channel',
                part='snippet',
                maxResults=1
            ).execute()
            
            logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False

    def _search_channel_by_handle(self, handle: str) -> Optional[str]:
        """Search for channel by handle with multiple strategies."""
        clean_handle = handle.lstrip('@')
        logger.info(f"Searching for channel with handle: {clean_handle}")
        
        # First, test if API is working
        if not self.test_api_connection():
            logger.error("API connection failed, cannot search for channel")
            return None
        
        # Strategy 1: Try the newer channels.list API with forHandle parameter (YouTube API v3.0+)
        try:
            logger.info(f"Trying forHandle API with: @{clean_handle}")
            response = self._retry_api_call(
                self.youtube.channels().list,
                part='snippet,statistics',
                forHandle=f"@{clean_handle}"
            )
            
            if response.get('items'):
                channel_id = response['items'][0]['id']
                logger.info(f"Found channel via forHandle: {channel_id}")
                return channel_id
        except HttpError as e:
            logger.warning(f"forHandle API failed (expected for older API versions): {e}")
        except Exception as e:
            logger.warning(f"forHandle API error: {e}")
        
        # Strategy 2: Try forUsername for legacy usernames
        try:
            logger.info(f"Trying forUsername API with: {clean_handle}")
            response = self._retry_api_call(
                self.youtube.channels().list,
                part='snippet,statistics',
                forUsername=clean_handle
            )
            
            if response.get('items'):
                channel_id = response['items'][0]['id']
                logger.info(f"Found channel via forUsername: {channel_id}")
                return channel_id
        except HttpError as e:
            logger.info(f"forUsername API failed: {e}")
        except Exception as e:
            logger.warning(f"forUsername API error: {e}")
        
        # Strategy 3: Basic search - simplified approach
        try:
            logger.info(f"Trying basic search for: {clean_handle}")
            response = self.youtube.search().list(
                q=clean_handle,
                type='channel',
                part='snippet',
                maxResults=10
            ).execute()
            
            logger.info(f"Basic search returned {len(response.get('items', []))} results")
            
            if response.get('items'):
                # Look through results for best match
                for item in response['items']:
                    channel_id = item['id']['channelId']
                    title = item['snippet']['title']
                    
                    logger.info(f"Found result: '{title}' -> {channel_id}")
                    
                    # Check for reasonable matches
                    title_lower = title.lower()
                    handle_lower = clean_handle.lower()
                    
                    if (handle_lower in title_lower or
                        title_lower in handle_lower or
                        any(word in title_lower for word in handle_lower.split()) and len(handle_lower.split()) > 1):
                        
                        logger.info(f"Matched channel: {title} -> {channel_id}")
                        return channel_id
                
                # If no good match found, return first result as fallback
                first_result = response['items'][0]
                first_channel_id = first_result['id']['channelId']
                first_title = first_result['snippet']['title']
                logger.info(f"Using first result as fallback: {first_title} -> {first_channel_id}")
                return first_channel_id
                
        except Exception as e:
            logger.error(f"Basic search failed: {e}")
        
        # Strategy 4: Try with quotes for exact match
        try:
            logger.info(f"Trying quoted search for: \"{clean_handle}\"")
            response = self.youtube.search().list(
                q=f'"{clean_handle}"',
                type='channel',
                part='snippet',
                maxResults=5
            ).execute()
            
            if response.get('items'):
                channel_id = response['items'][0]['id']['channelId']
                title = response['items'][0]['snippet']['title']
                logger.info(f"Found via quoted search: {title} -> {channel_id}")
                return channel_id
                
        except Exception as e:
            logger.error(f"Quoted search failed: {e}")
        
        logger.error(f"All search strategies failed for handle: {clean_handle}")
        return None

    def _try_direct_handle_resolution(self, handle: str) -> Optional[str]:
        """Try to resolve handle by testing different variations."""
        clean_handle = handle.lstrip('@')
        logger.info(f"Attempting direct handle resolution for: {clean_handle}")
        
        # Try searching using the handle and its basic transformations
        search_queries = [
            clean_handle,
            clean_handle.replace('_', ' '),
            clean_handle.replace('-', ' '),
            clean_handle.lower(),
        ]

        for query in search_queries:
            try:
                logger.info(f"Trying direct handle resolution with query: {query}")
                response = self.youtube.search().list(
                    q=query,
                    type='channel',
                    part='snippet',
                    maxResults=3
                ).execute()

                if response.get('items'):
                    for item in response['items']:
                        channel_id = item['id']['channelId']
                        title = item['snippet']['title']

                        # Check if the handle or its transformation is in the title
                        if clean_handle.lower() in title.lower() or query.lower() in title.lower():
                            logger.info(f"Direct resolution found match: {title} -> {channel_id}")
                            return channel_id

            except Exception as e:
                logger.debug(f"Direct resolution failed for query '{query}': {e}")
                continue

        logger.info(f"Direct handle resolution failed for: {clean_handle}")
        return None

    def _search_channel_by_query(self, query: str) -> Optional[str]:
        """Search for channel by query string."""
        try:
            response = self._retry_api_call(
                self.youtube.search().list,
                q=query,
                type='channel',
                part='id',
                maxResults=5
            )
            
            if response.get('items'):
                return response['items'][0]['id']['channelId']
        except HttpError as e:
            logger.error(f"Error searching for channel by query '{query}': {e}")
        return None

    def _get_channel_uploads_playlist_id(self, channel_id: str) -> Optional[str]:
        """Retrieves the uploads playlist ID for a channel."""
        try:
            response = self._retry_api_call(
                self.youtube.channels().list,
                part='contentDetails',
                id=channel_id
            )
            
            if response.get('items'):
                return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        except HttpError as e:
            logger.error(f"API error getting uploads playlist for channel {channel_id}: {e}")
        return None

    def _get_video_ids_from_playlist(self, playlist_id: str, max_results: int = None) -> List[str]:
        """Retrieves video IDs from a playlist with pagination."""
        if max_results is None:
            max_results = self.config.max_videos
            
        video_ids = []
        try:
            request = self.youtube.playlistItems().list(
                part='contentDetails',
                playlistId=playlist_id,
                maxResults=min(max_results, 50)
            )
            
            while request and len(video_ids) < max_results:
                response = request.execute()
                batch_ids = [item['contentDetails']['videoId'] for item in response.get('items', [])]
                video_ids.extend(batch_ids)
                
                if len(video_ids) >= max_results:
                    video_ids = video_ids[:max_results]
                    break
                    
                request = self.youtube.playlistItems().list_next(request, response)
                
        except HttpError as e:
            logger.error(f"API error for playlist {playlist_id}: {e}")
            
        return video_ids

    def _get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieves detailed information for video IDs in batches."""
        if not video_ids:
            return []
            
        details = []
        try:
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i:i + 50]
                response = self._retry_api_call(
                    self.youtube.videos().list,
                    part='snippet,statistics,contentDetails',
                    id=','.join(chunk)
                )
                details.extend(response.get('items', []))
        except HttpError as e:
            logger.error(f"API error getting video details: {e}")
            
        return details

    def _get_comments_for_video(self, video_id: str, max_comments: int = None) -> List[Dict[str, Any]]:
        """Retrieves comments for a video with better error handling."""
        if not self.config.enable_comments:
            return []
            
        if max_comments is None:
            max_comments = self.config.max_comments_per_video
            
        comments = []
        try:
            response = self._retry_api_call(
                self.youtube.commentThreads().list,
                part='snippet',
                videoId=video_id,
                maxResults=min(max_comments, 100),
                textFormat='plainText'
            )
            
            comments.extend(response.get('items', []))
            
        except HttpError as e:
            if e.resp.status == 403 and 'commentsDisabled' in str(e.content):
                logger.info(f"Comments disabled for video {video_id}")
            else:
                logger.error(f"API error getting comments for video {video_id}: {e}")
                
        return comments

    def _get_videos_with_comments_concurrent(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch comments for multiple videos concurrently."""
        if not self.config.enable_concurrent_fetching:
            return self._get_videos_with_comments_sequential(videos)
            
        def fetch_video_with_comments(video):
            comments = self._get_comments_for_video(video['id'])
            return {'video': video, 'comments': comments}
        
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            results = list(executor.map(fetch_video_with_comments, videos))
            
        return results

    def _get_videos_with_comments_sequential(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fetch comments for videos sequentially (fallback method)."""
        results = []
        for video in videos:
            comments = self._get_comments_for_video(video['id'])
            results.append({'video': video, 'comments': comments})
        return results

    def get_channel_data(self, channel_link: str) -> Dict[str, Any]:
        """Enhanced main function to fetch channel data."""
        logger.info(f"Starting data fetch for channel: {channel_link}")
        
        try:
            channel_id = self._extract_channel_id(channel_link)
            if not channel_id:
                raise YouTubeFetcherError(f"Could not extract channel ID from {channel_link}")

            # Get channel details
            channel_response = self._retry_api_call(
                self.youtube.channels().list,
                part='snippet,statistics,contentDetails',
                id=channel_id
            )
            
            if not channel_response.get('items'):
                raise YouTubeFetcherError(f"Channel {channel_id} not found")

            channel_details = channel_response['items'][0]
            
            # Get video data
            uploads_playlist_id = self._get_channel_uploads_playlist_id(channel_id)
            if not uploads_playlist_id:
                raise YouTubeFetcherError(f"Could not find uploads playlist for channel {channel_id}")

            video_ids = self._get_video_ids_from_playlist(uploads_playlist_id)
            if not video_ids:
                logger.warning(f"No videos found for channel {channel_id}")
                return {
                    "channel_id": channel_id,
                    "channel_details": channel_details,
                    "all_videos_summary": [],
                    "most_popular_videos_with_comments": [],
                    "least_popular_videos_with_comments": []
                }

            video_details = self._get_video_details(video_ids)
            
            # Sort by view count (handle missing statistics gracefully)
            video_details.sort(
                key=lambda x: int(x.get('statistics', {}).get('viewCount', 0)), 
                reverse=True
            )

            # Get top and bottom videos
            popular_count = min(self.config.popular_videos_count, len(video_details))
            least_popular_count = min(self.config.least_popular_videos_count, len(video_details))
            
            most_popular = video_details[:popular_count]
            least_popular = video_details[-least_popular_count:] if len(video_details) > popular_count else []

            return {
                "channel_id": channel_id,
                "channel_details": channel_details,
                "all_videos_summary": video_details,
                "most_popular_videos_with_comments": self._get_videos_with_comments_concurrent(most_popular),
                "least_popular_videos_with_comments": self._get_videos_with_comments_concurrent(least_popular)
            }

        except YouTubeFetcherError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error for channel {channel_link}")
            raise YouTubeFetcherError(f"Unexpected error: {str(e)}")

    def get_video_data(self, video_link: str) -> Dict[str, Any]:
        """Enhanced function to fetch video data."""
        logger.info(f"Starting data fetch for video: {video_link}")
        
        try:
            video_id = self._extract_video_id(video_link)
            if not video_id:
                raise YouTubeFetcherError(f"Could not extract video ID from {video_link}")

            video_details_list = self._get_video_details([video_id])
            if not video_details_list:
                raise YouTubeFetcherError(f"Video {video_id} not found")

            current_video_details = video_details_list[0]
            channel_id = current_video_details.get('snippet', {}).get('channelId')
            
            if not channel_id:
                raise YouTubeFetcherError(f"Could not determine channel ID for video {video_id}")

            # Get channel data
            channel_data = self.get_channel_data(f"https://www.youtube.com/channel/{channel_id}")
            
            # Get comments for current video
            current_video_comments = self._get_comments_for_video(video_id)

            return {
                **channel_data,
                "current_video_details": current_video_details,
                "current_video_comments": current_video_comments
            }

        except YouTubeFetcherError:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error for video {video_link}")
            raise YouTubeFetcherError(f"Unexpected error: {str(e)}")

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        logger.info("Cache cleared")