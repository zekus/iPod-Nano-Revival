#!/usr/bin/env python3
"""
YouTube Downloader Module for iPod Nano Transfer Tool
Handles downloading audio from YouTube videos and playlists
"""

import os
import re
import logging
import time
from typing import List, Dict, Optional, Tuple, Callable
from dataclasses import dataclass

import yt_dlp
from tqdm import tqdm

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class TrackInfo:
    """Data class to store track information"""
    video_id: str
    title: str
    artist: str
    album: str
    thumbnail_url: str
    duration: int
    track_number: Optional[int] = None
    playlist_id: Optional[str] = None
    playlist_title: Optional[str] = None
    playlist_index: Optional[int] = None
    download_path: Optional[str] = None


class YouTubeDownloader:
    """Class to handle YouTube video and playlist downloads"""
    
    def __init__(self, output_dir: str = "downloads", temp_dir: str = "temp", progress_callback: Optional[Callable] = None):
        """
        Initialize the YouTube downloader
        
        Args:
            output_dir: Directory to save downloaded files
            temp_dir: Directory for temporary files
            progress_callback: Optional callback function for progress updates
        """
        self.output_dir = output_dir
        self.temp_dir = temp_dir
        self.progress_callback = progress_callback
        
        # Create directories if they don't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Playlist regex pattern
        self.playlist_regex = r'(?:list=)([a-zA-Z0-9_-]+)'
        
        # Track download progress
        self.download_start_time = 0
        self.current_track = None
        
    def _parse_artist_title(self, video_title: str) -> Tuple[str, str]:
        """
        Parse artist and title from video title
        
        Args:
            video_title: YouTube video title
            
        Returns:
            Tuple of (artist, title)
        """
        # Common patterns: "Artist - Title", "Artist: Title", "Artist | Title"
        patterns = [
            r'^(.*?)\s*-\s*(.*?)$',  # Artist - Title
            r'^(.*?)\s*:\s*(.*?)$',  # Artist: Title
            r'^(.*?)\s*\|\s*(.*?)$'  # Artist | Title
        ]
        
        for pattern in patterns:
            match = re.match(pattern, video_title)
            if match:
                artist, title = match.groups()
                return artist.strip(), title.strip()
        
        # If no pattern matches, return empty artist and full title
        return "", video_title.strip()
    
    def extract_video_info(self, video_url: str) -> Optional[TrackInfo]:
        """
        Extract information from a YouTube video
        
        Args:
            video_url: YouTube video URL
            
        Returns:
            TrackInfo object with video metadata or None if video is unavailable
        """
        logger.info(f"Extracting info from video: {video_url}")
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': True,
            'ignoreerrors': True,  # Continue on download errors
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(video_url, download=False)
                
                if not info:
                    logger.warning(f"Could not extract info from video: {video_url}")
                    return None
                    
                video_id = info.get('id')
                video_title = info.get('title', '')
                artist, title = self._parse_artist_title(video_title)
                
                # Get best thumbnail
                thumbnails = info.get('thumbnails', [])
                thumbnail_url = next((t['url'] for t in reversed(thumbnails) 
                                    if 'url' in t), None) if thumbnails else None
                
                return TrackInfo(
                    video_id=video_id,
                    title=title,
                    artist=artist,
                    album=artist,  # Default album to artist name
                    thumbnail_url=thumbnail_url,
                    duration=info.get('duration', 0)
                )
        except Exception as e:
            logger.warning(f"Error extracting video info: {e}")
            return None
    
    def extract_playlist_info(self, playlist_url: str) -> List[TrackInfo]:
        """
        Extract information from a YouTube playlist
        
        Args:
            playlist_url: YouTube playlist URL
            
        Returns:
            List of TrackInfo objects for each video in the playlist
        """
        logger.info(f"Extracting info from playlist: {playlist_url}")
        
        # Extract playlist ID
        playlist_id_match = re.search(self.playlist_regex, playlist_url)
        if not playlist_id_match:
            raise ValueError(f"Invalid playlist URL: {playlist_url}")
            
        playlist_id = playlist_id_match.group(1)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'skip_download': True,
            'ignoreerrors': True,  # Continue on download errors
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(
                    f'https://www.youtube.com/playlist?list={playlist_id}',
                    download=False
                )
                
                if not playlist_info or 'entries' not in playlist_info:
                    logger.warning(f"Could not extract playlist info: {playlist_url}")
                    return []
                
                playlist_title = playlist_info.get('title', 'Unknown Playlist')
                tracks = []
                track_number = 1  # Keep track of actual track numbers
                
                # Update progress if callback is available
                if self.progress_callback:
                    self.progress_callback(0, f"Analyzing playlist: {playlist_title}")
                
                total_entries = len(playlist_info.get('entries', []))
                
                for idx, entry in enumerate(playlist_info.get('entries', []), 1):
                    # Update progress for playlist analysis
                    if self.progress_callback:
                        progress = int((idx / total_entries) * 10)  # Use first 10% for playlist analysis
                        self.progress_callback(progress, f"Analyzing playlist: {idx}/{total_entries} tracks")
                    
                    if not entry or entry.get('_type') != 'url':
                        continue
                    
                    try:
                        video_info = self.extract_video_info(f"https://www.youtube.com/watch?v={entry['id']}")
                        if video_info:
                            video_info.playlist_id = playlist_id
                            video_info.playlist_title = playlist_title
                            video_info.playlist_index = idx
                            video_info.track_number = track_number
                            video_info.album = playlist_title  # Set album to playlist title
                            tracks.append(video_info)
                            track_number += 1
                        else:
                            logger.warning(f"Skipping unavailable video in playlist: {entry.get('id')}")
                    except Exception as e:
                        logger.warning(f"Error processing playlist entry {idx}: {e}")
                
                return tracks
        except Exception as e:
            logger.error(f"Error extracting playlist info: {e}")
            return []
    
    def download_audio(self, track_info: TrackInfo, format: str = "m4a", quality: int = 256) -> Optional[str]:
        """
        Download audio from YouTube video
        
        Args:
            track_info: TrackInfo object with video metadata
            format: Audio format (m4a, mp3)
            quality: Audio quality in kbps
            
        Returns:
            Path to downloaded file or None if download failed
        """
        logger.info(f"Downloading audio for: {track_info.title}")
        self.current_track = track_info
        self.download_start_time = time.time()
        
        # Create output filename
        safe_title = re.sub(r'[^\w\-_\. ]', '_', track_info.title)
        if track_info.track_number:
            filename = f"{track_info.track_number:02d}. {safe_title}.{format}"
        else:
            filename = f"{safe_title}.{format}"
            
        output_path = os.path.join(self.temp_dir, filename)
        
        # Set up yt-dlp options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format,
                'preferredquality': str(quality),
            }],
            'quiet': False,
            'progress_hooks': [self._download_progress_hook],
            'ignoreerrors': True,  # Continue on download errors
        }
        
        try:
            # Download the file
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={track_info.video_id}"])
            
            # Check if file was actually downloaded
            expected_path = f"{output_path}.{format}"
            if os.path.exists(expected_path):
                # Update track_info with download path
                track_info.download_path = expected_path
                return track_info.download_path
            else:
                logger.warning(f"Download failed for: {track_info.title}")
                return None
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None
    
    def _download_progress_hook(self, d: Dict):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            # Calculate download progress
            if 'total_bytes' in d and d['total_bytes'] > 0:
                percent = d['downloaded_bytes'] / d['total_bytes'] * 100
                
                # Calculate download speed
                elapsed_time = time.time() - self.download_start_time
                if elapsed_time > 0:
                    download_speed = d['downloaded_bytes'] / elapsed_time / 1024  # KB/s
                    
                    # Format download speed
                    speed_str = f"{download_speed:.1f} KB/s"
                    if download_speed > 1024:
                        speed_str = f"{download_speed/1024:.1f} MB/s"
                    
                    # Format file size
                    total_size_mb = d['total_bytes'] / (1024 * 1024)
                    downloaded_mb = d['downloaded_bytes'] / (1024 * 1024)
                    
                    # Create status message
                    status_msg = f"Downloading {self.current_track.title}: {downloaded_mb:.1f}/{total_size_mb:.1f} MB ({percent:.1f}%) at {speed_str}"
                    
                    # Log progress
                    logger.info(status_msg)
                    
                    # Call progress callback if available
                    if self.progress_callback:
                        # Scale to 10-95% range to leave room for playlist analysis and completion
                        scaled_percent = 10 + (percent * 0.85)
                        self.progress_callback(int(scaled_percent), status_msg)
                    
            # If we don't have total_bytes, show indeterminate progress
            elif 'downloaded_bytes' in d:
                elapsed_time = time.time() - self.download_start_time
                if elapsed_time > 0:
                    download_speed = d['downloaded_bytes'] / elapsed_time / 1024  # KB/s
                    
                    # Format download speed
                    speed_str = f"{download_speed:.1f} KB/s"
                    if download_speed > 1024:
                        speed_str = f"{download_speed/1024:.1f} MB/s"
                    
                    # Format file size
                    downloaded_mb = d['downloaded_bytes'] / (1024 * 1024)
                    
                    # Create status message
                    status_msg = f"Downloading {self.current_track.title}: {downloaded_mb:.1f} MB at {speed_str}"
                    
                    # Log progress
                    logger.info(status_msg)
                    
                    # Call progress callback if available
                    if self.progress_callback:
                        # Use a pulsing progress between 10-90% for indeterminate progress
                        pulse_progress = 10 + (int(time.time() * 10) % 80)
                        self.progress_callback(pulse_progress, status_msg)
        
        elif d['status'] == 'finished':
            logger.info(f"Download complete: {self.current_track.title}")
            if self.progress_callback:
                self.progress_callback(95, f"Download complete: {self.current_track.title}")
        
        elif d['status'] == 'error':
            logger.warning(f"Download error: {self.current_track.title}")
            if self.progress_callback:
                self.progress_callback(95, f"Download error: {self.current_track.title}")
    
    def process_url(self, url: str, format: str = "m4a", quality: int = 256) -> List[TrackInfo]:
        """
        Process a YouTube URL (video or playlist)
        
        Args:
            url: YouTube URL
            format: Audio format
            quality: Audio quality in kbps
            
        Returns:
            List of TrackInfo objects with download paths
        """
        successful_tracks = []
        
        try:
            # Check if URL is a playlist
            if 'list=' in url:
                # Process as playlist
                tracks = self.extract_playlist_info(url)
                
                if not tracks:
                    logger.warning("No valid tracks found in playlist")
                    return []
                
                # Download each track
                for i, track in enumerate(tracks):
                    if self.progress_callback:
                        status_msg = f"Preparing to download {i+1}/{len(tracks)}: {track.title}"
                        self.progress_callback(10, status_msg)
                    
                    try:
                        download_path = self.download_audio(track, format, quality)
                        if download_path:
                            successful_tracks.append(track)
                    except Exception as e:
                        logger.error(f"Error downloading track {track.title}: {e}")
                
            else:
                # Process as single video
                track = self.extract_video_info(url)
                if track:
                    try:
                        download_path = self.download_audio(track, format, quality)
                        if download_path:
                            successful_tracks.append(track)
                    except Exception as e:
                        logger.error(f"Error downloading track {track.title}: {e}")
                else:
                    logger.warning("Could not extract video information")
            
            # Final progress update
            if self.progress_callback:
                self.progress_callback(100, f"Downloaded {len(successful_tracks)} tracks successfully")
            
            return successful_tracks
            
        except Exception as e:
            logger.error(f"Error processing URL: {e}")
            if self.progress_callback:
                self.progress_callback(100, f"Error: {str(e)}")
            return successful_tracks


if __name__ == "__main__":
    # Example usage
    downloader = YouTubeDownloader()
    
    # Test with a single video
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    video_info = downloader.extract_video_info(video_url)
    print(f"Video: {video_info.artist} - {video_info.title}")
    
    # Uncomment to test download
    # downloader.download_audio(video_info)
