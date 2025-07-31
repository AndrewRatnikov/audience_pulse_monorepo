from urllib.parse import urlparse, parse_qs
from typing import Optional, List, Dict, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from ..logger import logger

class YouTubeFetcher:
    """A class to fetch data from the YouTube Data API v3."""

    def __init__(self, api_key: str):
        """Initializes the YouTubeFetcher with an API key."""
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def _extract_channel_id(self, youtube_link: str) -> Optional[str]:
        """Extracts the YouTube channel ID from various URL formats."""
        parsed_url = urlparse(youtube_link)
        path_parts = parsed_url.path.split('/')

        if 'watch' in parsed_url.path:
            video_id = parse_qs(parsed_url.query).get('v', [None])[0]
            if video_id:
                video_details = self._get_video_details([video_id])
                if video_details:
                    return video_details[0].get('snippet', {}).get('channelId')
        elif '/channel/' in parsed_url.path:
            return path_parts[-1]
        elif parsed_url.path.startswith('/@'):
            handle = parsed_url.path[2:]
            try:
                search_response = self.youtube.search().list(forHandle=handle, part='id').execute()
                if search_response.get('items'):
                    return search_response['items'][0]['id']['channelId']
            except HttpError as e:
                logger.error(f"_extract_channel_id: Error searching for channel by handle '{handle}': {e}")
        else: # Fallback for /c/, /user/, or other formats
            query = path_parts[-1]
            try:
                search_response = self.youtube.search().list(q=query, type='channel', part='id').execute()
                if search_response.get('items'):
                    return search_response['items'][0]['id']['channelId']
            except HttpError as e:
                logger.error(f"_extract_channel_id: Error searching for channel by query '{query}': {e}")

        logger.warning(f"_extract_channel_id: Could not determine channel ID from link: {youtube_link}")
        return None

    def _get_channel_uploads_playlist_id(self, channel_id: str) -> Optional[str]:
        """Retrieves the ID of the 'uploads' playlist for a given channel."""
        try:
            response = self.youtube.channels().list(part='contentDetails', id=channel_id).execute()
            if response.get('items'):
                return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        except HttpError as e:
            logger.error(f"_get_channel_uploads_playlist_id: API error for channel {channel_id}: {e}")
        return None

    def _get_video_ids_from_playlist(self, playlist_id: str, max_results: int = 50) -> List[str]:
        """Retrieves a list of video IDs from a specified playlist."""
        video_ids = []
        try:
            request = self.youtube.playlistItems().list(
                part='contentDetails', playlistId=playlist_id, maxResults=min(max_results, 50)
            )
            while request and len(video_ids) < max_results:
                response = request.execute()
                video_ids.extend([item['contentDetails']['videoId'] for item in response.get('items', [])])
                request = self.youtube.playlistItems().list_next(request, response)
        except HttpError as e:
            logger.error(f"_get_video_ids_from_playlist: API error for playlist {playlist_id}: {e}")
        return video_ids

    def _get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Retrieves detailed information for a list of video IDs."""
        details = []
        if not video_ids:
            return details
        try:
            for i in range(0, len(video_ids), 50):
                chunk = video_ids[i:i + 50]
                response = self.youtube.videos().list(
                    part='snippet,statistics,contentDetails', id=','.join(chunk)
                ).execute()
                details.extend(response.get('items', []))
        except HttpError as e:
            logger.error(f"_get_video_details: API error for video IDs: {e}")
        return details

    def _get_comments_for_video(self, video_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """Retrieves top-level comments for a given video."""
        comments = []
        try:
            request = self.youtube.commentThreads().list(
                part='snippet', videoId=video_id, maxResults=min(max_comments, 100), textFormat='plainText'
            )
            response = request.execute()
            comments.extend(response.get('items', []))
        except HttpError as e:
            # Gracefully handle disabled comments
            if e.resp.status == 403 and 'commentsDisabled' in str(e.content):
                logger.warning(f"_get_comments_for_video: Comments are disabled for video {video_id}")
            else:
                logger.error(f"_get_comments_for_video: API error for video {video_id}: {e}")
        return comments

    def _get_videos_with_comments(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Helper to fetch comments for a list of videos."""
        videos_with_comments = []
        for video in videos:
            comments = self._get_comments_for_video(video['id'])
            videos_with_comments.append({'video': video, 'comments': comments})
        return videos_with_comments

    def get_channel_data(self, channel_link: str) -> Dict[str, Any]:
        """Main function to orchestrate fetching all data for a channel link."""
        logger.info(f"get_channel_data: Starting data fetch for channel link: {channel_link}")
        channel_id = self._extract_channel_id(channel_link)
        if not channel_id:
            return {"error": f"Could not extract a valid channel ID from {channel_link}"}

        try:
            channel_response = self.youtube.channels().list(
                part='snippet,statistics,contentDetails', id=channel_id
            ).execute()
            if not channel_response.get('items'):
                return {"error": f"Channel with ID {channel_id} not found."}

            channel_details = channel_response['items'][0]
            uploads_playlist_id = self._get_channel_uploads_playlist_id(channel_id)
            if not uploads_playlist_id:
                return {"error": f"Could not find uploads playlist for channel {channel_id}"}

            video_ids = self._get_video_ids_from_playlist(uploads_playlist_id, max_results=200)
            if not video_ids:
                return {"error": f"No videos found for channel {channel_id}"}

            video_details = self._get_video_details(video_ids)
            video_details.sort(key=lambda x: int(x.get('statistics', {}).get('viewCount', 0)), reverse=True)

            most_popular_videos = video_details[:5]
            least_popular_videos = video_details[-5:]

            return {
                "channel_id": channel_id,
                "channel_statistics": channel_details.get('statistics'),
                "all_videos_summary": video_details,
                "most_popular_videos_with_comments": self._get_videos_with_comments(most_popular_videos),
                "least_popular_videos_with_comments": self._get_videos_with_comments(least_popular_videos)
            }

        except HttpError as e:
            logger.error(f"get_channel_data: A critical API error occurred for channel {channel_id}: {e}")
            return {"error": f"API Error: {e.content.decode('utf-8')}"}
        except Exception as e:
            logger.exception(f"get_channel_data: An unexpected error occurred for channel {channel_id}")
            return {"error": "An unexpected error occurred."}

    def get_video_data(self, video_link: str) -> Dict[str, Any]:
        """Main function to orchestrate fetching all data for a video link."""
        logger.info(f"get_video_data: Starting data fetch for video link: {video_link}")
        video_id_match = parse_qs(urlparse(video_link).query).get('v', [None])
        video_id = video_id_match[0] if video_id_match else urlparse(video_link).path.lstrip('/')

        if not video_id:
            return {"error": f"Could not extract a valid video ID from {video_link}"}

        video_details_list = self._get_video_details([video_id])
        if not video_details_list:
            return {"error": f"Video with ID {video_id} not found."}

        current_video_details = video_details_list[0]
        channel_id = current_video_details.get('snippet', {}).get('channelId')
        if not channel_id:
            return {"error": f"Could not determine channel ID for video {video_id}"}

        channel_data = self.get_channel_data(f"https://www.youtube.com/channel/{channel_id}")
        if 'error' in channel_data:
            # If channel data fetching fails, return the error but add video context
            channel_data['current_video_details'] = current_video_details
            return channel_data

        current_video_comments = self._get_comments_for_video(video_id)

        return {
            **channel_data,
            "current_video_details": current_video_details,
            "current_video_comments": current_video_comments
        }