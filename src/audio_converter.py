#!/usr/bin/env python3
"""
Audio Converter Module for iPod Nano Transfer Tool
Handles converting audio files to iPod-compatible formats
"""

import os
import logging
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

import ffmpeg

from youtube_downloader import TrackInfo

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class AudioConverter:
    """Class to handle audio conversion to iPod-compatible formats"""
    
    def __init__(self, output_dir: str = "converted"):
        """
        Initialize the audio converter
        
        Args:
            output_dir: Directory to save converted files
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Check if ffmpeg is installed
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        except (subprocess.SubprocessError, FileNotFoundError):
            logger.error("FFmpeg is not installed or not in PATH. Please install FFmpeg.")
            raise RuntimeError("FFmpeg is required but not found")
    
    def convert_to_ipod_format(self, 
                              track_info: TrackInfo, 
                              input_file: str,
                              format: str = "m4a", 
                              audio_bitrate: int = 256,
                              overwrite: bool = False) -> str:
        """
        Convert audio file to iPod-compatible format
        
        Args:
            track_info: TrackInfo object with track metadata
            input_file: Path to input audio file
            format: Output format (m4a, mp3)
            audio_bitrate: Audio bitrate in kbps
            overwrite: Whether to overwrite existing files
            
        Returns:
            Path to converted file
        """
        logger.info(f"Converting {input_file} to iPod-compatible {format}")
        
        # Create output directory structure
        if track_info.playlist_title:
            # For playlist tracks: Artist/Playlist/01 - Track.m4a
            artist_dir = os.path.join(self.output_dir, self._sanitize_filename(track_info.artist))
            album_dir = os.path.join(artist_dir, self._sanitize_filename(track_info.playlist_title))
            os.makedirs(album_dir, exist_ok=True)
            
            if track_info.track_number:
                filename = f"{track_info.track_number:02d} - {self._sanitize_filename(track_info.title)}.{format}"
            else:
                filename = f"{self._sanitize_filename(track_info.title)}.{format}"
                
            output_file = os.path.join(album_dir, filename)
        else:
            # For single tracks: Artist/Artist/Track.m4a
            artist_dir = os.path.join(self.output_dir, self._sanitize_filename(track_info.artist))
            album_dir = os.path.join(artist_dir, self._sanitize_filename(track_info.album or track_info.artist))
            os.makedirs(album_dir, exist_ok=True)
            
            filename = f"{self._sanitize_filename(track_info.title)}.{format}"
            output_file = os.path.join(album_dir, filename)
        
        # Check if file already exists
        if os.path.exists(output_file) and not overwrite:
            logger.info(f"File already exists: {output_file}")
            return output_file
        
        # Set up FFmpeg conversion
        try:
            # Input file
            stream = ffmpeg.input(input_file)
            
            # Output options
            audio_options: Dict[str, Any] = {
                'acodec': 'aac' if format == 'm4a' else 'libmp3lame',
                'b:a': f'{audio_bitrate}k',
                'map_metadata': 0,
            }
            
            # Run conversion
            stream = ffmpeg.output(stream, output_file, **audio_options)
            ffmpeg.run(stream, overwrite_output=overwrite, quiet=True)
            
            logger.info(f"Conversion complete: {output_file}")
            return output_file
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            raise
    
    def convert_video_for_ipod(self,
                              input_file: str,
                              output_file: Optional[str] = None,
                              resolution: str = "640x480",
                              video_bitrate: int = 1500,
                              audio_bitrate: int = 256,
                              overwrite: bool = False) -> str:
        """
        Convert video file to iPod-compatible format
        
        Args:
            input_file: Path to input video file
            output_file: Path to output file (optional)
            resolution: Video resolution (max 640x480 for iPod Nano)
            video_bitrate: Video bitrate in kbps
            audio_bitrate: Audio bitrate in kbps
            overwrite: Whether to overwrite existing files
            
        Returns:
            Path to converted file
        """
        logger.info(f"Converting video {input_file} to iPod-compatible format")
        
        if not output_file:
            input_path = Path(input_file)
            output_file = os.path.join(self.output_dir, f"{input_path.stem}_ipod.mp4")
        
        # Check if file already exists
        if os.path.exists(output_file) and not overwrite:
            logger.info(f"File already exists: {output_file}")
            return output_file
        
        # Set up FFmpeg conversion
        try:
            # Input file
            stream = ffmpeg.input(input_file)
            
            # Output options
            video_options = {
                'vcodec': 'h264',
                'b:v': f'{video_bitrate}k',
                'acodec': 'aac',
                'b:a': f'{audio_bitrate}k',
                'vf': f'scale={resolution}',
                'pix_fmt': 'yuv420p',  # Required for compatibility
                'map_metadata': 0,
            }
            
            # Run conversion
            stream = ffmpeg.output(stream, output_file, **video_options)
            ffmpeg.run(stream, overwrite_output=overwrite, quiet=True)
            
            logger.info(f"Video conversion complete: {output_file}")
            return output_file
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            raise
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to be compatible with file systems
        
        Args:
            filename: Input filename
            
        Returns:
            Sanitized filename
        """
        # Replace invalid characters with underscore
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Limit length
        if len(filename) > 100:
            filename = filename[:97] + '...'
            
        return filename.strip()


if __name__ == "__main__":
    # Example usage
    converter = AudioConverter()
    
    # Test audio conversion
    # converter.convert_to_ipod_format(
    #     TrackInfo(
    #         video_id="dQw4w9WgXcQ",
    #         title="Never Gonna Give You Up",
    #         artist="Rick Astley",
    #         album="Whenever You Need Somebody",
    #         thumbnail_url="",
    #         duration=213
    #     ),
    #     "input.mp3"
    # )
    
    # Test video conversion
    # converter.convert_video_for_ipod("input.mp4")
