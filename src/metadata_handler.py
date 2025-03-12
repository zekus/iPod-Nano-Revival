#!/usr/bin/env python3
"""
Metadata Handler Module for iPod Nano Transfer Tool
Handles metadata injection and album art embedding
"""

import os
import logging
import tempfile
from typing import Optional, Dict, Any
from io import BytesIO
from pathlib import Path

import requests
from PIL import Image
from mutagen.mp4 import MP4, MP4Cover
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB, TRCK
from mutagen.easyid3 import EasyID3

from youtube_downloader import TrackInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MetadataHandler:
    """Class to handle metadata injection and album art embedding"""
    
    def __init__(self, temp_dir: Optional[str] = None):
        """
        Initialize the metadata handler
        
        Args:
            temp_dir: Directory for temporary files (optional)
        """
        self.temp_dir = temp_dir or tempfile.gettempdir()
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def download_thumbnail(self, thumbnail_url: str) -> Optional[str]:
        """
        Download thumbnail image from URL
        
        Args:
            thumbnail_url: URL of the thumbnail image
            
        Returns:
            Path to downloaded thumbnail file, or None if download failed
        """
        if not thumbnail_url:
            logger.warning("No thumbnail URL provided")
            return None
            
        try:
            logger.info(f"Downloading thumbnail: {thumbnail_url}")
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()
            
            # Save thumbnail to temporary file
            thumbnail_path = os.path.join(self.temp_dir, f"thumbnail_{hash(thumbnail_url)}.jpg")
            
            # Process image with PIL to ensure it's a valid format
            img = Image.open(BytesIO(response.content))
            img.save(thumbnail_path, "JPEG")
            
            logger.info(f"Thumbnail saved to: {thumbnail_path}")
            return thumbnail_path
            
        except (requests.RequestException, IOError) as e:
            logger.error(f"Failed to download thumbnail: {e}")
            return None
    
    def embed_metadata_m4a(self, 
                          file_path: str, 
                          track_info: TrackInfo,
                          thumbnail_path: Optional[str] = None) -> bool:
        """
        Embed metadata and album art in M4A/AAC file
        
        Args:
            file_path: Path to M4A/AAC file
            track_info: TrackInfo object with track metadata
            thumbnail_path: Path to thumbnail image (optional)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Embedding metadata in M4A file: {file_path}")
        
        try:
            audio = MP4(file_path)
            
            # Clear existing tags
            audio.clear()
            
            # Add metadata tags
            audio['\xa9nam'] = [track_info.title]  # Title
            audio['\xa9ART'] = [track_info.artist]  # Artist
            audio['\xa9alb'] = [track_info.album or track_info.artist]  # Album
            
            # Add track number if available
            if track_info.track_number is not None:
                audio['trkn'] = [(track_info.track_number, 0)]
            
            # Add album art if available
            if thumbnail_path:
                with open(thumbnail_path, 'rb') as f:
                    album_art_data = f.read()
                    
                # Determine image format
                if album_art_data.startswith(b'\xff\xd8'):
                    # JPEG
                    cover = MP4Cover(album_art_data, imageformat=MP4Cover.FORMAT_JPEG)
                else:
                    # PNG
                    cover = MP4Cover(album_art_data, imageformat=MP4Cover.FORMAT_PNG)
                
                audio['covr'] = [cover]
            
            # Save changes
            audio.save()
            logger.info(f"Metadata embedded successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to embed metadata in M4A file: {e}")
            return False
    
    def embed_metadata_mp3(self, 
                          file_path: str, 
                          track_info: TrackInfo,
                          thumbnail_path: Optional[str] = None) -> bool:
        """
        Embed metadata and album art in MP3 file
        
        Args:
            file_path: Path to MP3 file
            track_info: TrackInfo object with track metadata
            thumbnail_path: Path to thumbnail image (optional)
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Embedding metadata in MP3 file: {file_path}")
        
        try:
            # First try with EasyID3 for basic tags
            try:
                audio = EasyID3(file_path)
            except:
                # If the file doesn't have an ID3 tag, add one
                audio = ID3()
                audio.save(file_path)
                audio = EasyID3(file_path)
            
            # Clear existing tags
            audio.clear()
            
            # Add metadata tags
            audio['title'] = track_info.title
            audio['artist'] = track_info.artist
            audio['album'] = track_info.album or track_info.artist
            
            # Add track number if available
            if track_info.track_number is not None:
                audio['tracknumber'] = str(track_info.track_number)
            
            # Save basic tags
            audio.save()
            
            # Now add album art using ID3
            if thumbnail_path:
                audio = ID3(file_path)
                
                with open(thumbnail_path, 'rb') as f:
                    album_art_data = f.read()
                
                # Add album art
                audio.add(
                    APIC(
                        encoding=3,  # UTF-8
                        mime='image/jpeg',
                        type=3,  # Cover (front)
                        desc='Cover',
                        data=album_art_data
                    )
                )
                
                # Save with album art
                audio.save()
            
            logger.info(f"Metadata embedded successfully: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to embed metadata in MP3 file: {e}")
            return False
    
    def process_file(self, 
                    file_path: str, 
                    track_info: TrackInfo) -> bool:
        """
        Process audio file to embed metadata and album art
        
        Args:
            file_path: Path to audio file
            track_info: TrackInfo object with track metadata
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Processing metadata for file: {file_path}")
        
        # Download thumbnail if available
        thumbnail_path = None
        if track_info.thumbnail_url:
            thumbnail_path = self.download_thumbnail(track_info.thumbnail_url)
        
        # Determine file type and process accordingly
        file_ext = Path(file_path).suffix.lower()
        
        if file_ext in ['.m4a', '.aac', '.mp4']:
            return self.embed_metadata_m4a(file_path, track_info, thumbnail_path)
        elif file_ext == '.mp3':
            return self.embed_metadata_mp3(file_path, track_info, thumbnail_path)
        else:
            logger.warning(f"Unsupported file format: {file_ext}")
            return False
    
    def enhance_metadata_with_musicbrainz(self, track_info: TrackInfo) -> TrackInfo:
        """
        Enhance track metadata using MusicBrainz API
        
        Args:
            track_info: TrackInfo object with track metadata
            
        Returns:
            Enhanced TrackInfo object
        """
        # This is a placeholder for future implementation
        # MusicBrainz integration would go here
        return track_info


if __name__ == "__main__":
    # Example usage
    handler = MetadataHandler()
    
    # Test metadata embedding
    # handler.process_file(
    #     "test.m4a",
    #     TrackInfo(
    #         video_id="dQw4w9WgXcQ",
    #         title="Never Gonna Give You Up",
    #         artist="Rick Astley",
    #         album="Whenever You Need Somebody",
    #         thumbnail_url="https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
    #         duration=213,
    #         track_number=1
    #     )
    # )
