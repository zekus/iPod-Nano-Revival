#!/usr/bin/env python3
"""
Command Line Interface for iPod Nano Transfer Tool
Provides a CLI for the YouTube Music to iPod Nano transfer tool
"""

import os
import sys
import logging
import argparse
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from tqdm import tqdm

from youtube_downloader import YouTubeDownloader, TrackInfo
from audio_converter import AudioConverter
from metadata_handler import MetadataHandler
from ipod_device import IPodDevice

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class YouTubeToIPodCLI:
    """Command Line Interface for YouTube to iPod Nano Transfer Tool"""
    
    def __init__(self):
        """Initialize the CLI"""
        self.downloader = None
        self.converter = None
        self.metadata_handler = None
        self.ipod_device = None
        
        self.downloaded_tracks = []
        self.converted_tracks = []
        
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def parse_arguments(self):
        """Parse command line arguments"""
        parser = argparse.ArgumentParser(
            description="YouTube to iPod Nano Transfer Tool",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        
        # URL argument
        parser.add_argument(
            "--url", "-u",
            help="YouTube video or playlist URL",
            required=True
        )
        
        # Output directory
        parser.add_argument(
            "--output-dir", "-o",
            help="Output directory (iPod mount point)",
            default=os.path.join(os.path.expanduser("~"), "Music", "iPod")
        )
        
        # Format
        parser.add_argument(
            "--format", "-f",
            help="Audio format",
            choices=["m4a", "mp3"],
            default="m4a"
        )
        
        # Quality
        parser.add_argument(
            "--quality", "-q",
            help="Audio quality in kbps",
            type=int,
            choices=[128, 192, 256, 320],
            default=256
        )
        
        # Video support
        parser.add_argument(
            "--video",
            help="Enable video download (for compatible iPod models)",
            action="store_true"
        )
        
        # Video resolution
        parser.add_argument(
            "--resolution", "-r",
            help="Video resolution (for video download)",
            choices=["640x480", "480x360", "320x240"],
            default="640x480"
        )
        
        # iPod device
        parser.add_argument(
            "--device", "-d",
            help="iPod device mount point (if not specified, auto-detection will be attempted)",
            default=None
        )
        
        # Skip steps
        parser.add_argument(
            "--skip-download",
            help="Skip download step (use previously downloaded files)",
            action="store_true"
        )
        
        parser.add_argument(
            "--skip-convert",
            help="Skip conversion step (use previously converted files)",
            action="store_true"
        )
        
        parser.add_argument(
            "--skip-transfer",
            help="Skip transfer step (only download and convert)",
            action="store_true"
        )
        
        # Clean temp files
        parser.add_argument(
            "--clean-temp",
            help="Clean temporary files after transfer",
            action="store_true"
        )
        
        return parser.parse_args()
    
    def download(self, url: str, format: str = "m4a", quality: int = 256, video: bool = False) -> List[TrackInfo]:
        """
        Download audio/video from YouTube
        
        Args:
            url: YouTube URL
            format: Audio format
            quality: Audio quality in kbps
            video: Whether to download video
            
        Returns:
            List of TrackInfo objects
        """
        logger.info(f"Downloading from URL: {url}")
        
        # Initialize downloader
        self.downloader = YouTubeDownloader(output_dir=self.temp_dir)
        
        # Process URL
        tracks = self.downloader.process_url(url, format, quality)
        
        logger.info(f"Downloaded {len(tracks)} tracks")
        return tracks
    
    def convert(self, 
               tracks: List[TrackInfo], 
               output_dir: str, 
               format: str = "m4a", 
               quality: int = 256,
               video: bool = False,
               resolution: str = "640x480") -> List[Tuple[TrackInfo, str]]:
        """
        Convert downloaded tracks to iPod-compatible format
        
        Args:
            tracks: List of TrackInfo objects
            output_dir: Output directory
            format: Audio format
            quality: Audio quality in kbps
            video: Whether to convert video
            resolution: Video resolution
            
        Returns:
            List of (TrackInfo, output_path) tuples
        """
        logger.info(f"Converting {len(tracks)} tracks to iPod-compatible format")
        
        # Initialize converter and metadata handler
        self.converter = AudioConverter(output_dir=output_dir)
        self.metadata_handler = MetadataHandler(temp_dir=self.temp_dir)
        
        # Convert each track
        converted_tracks = []
        for track in tqdm(tracks, desc="Converting", unit="track"):
            if track.download_path and os.path.exists(track.download_path):
                # Convert to iPod format
                output_path = self.converter.convert_to_ipod_format(
                    track, track.download_path, format, quality
                )
                
                # Embed metadata
                if output_path:
                    self.metadata_handler.process_file(output_path, track)
                    converted_tracks.append((track, output_path))
        
        logger.info(f"Converted {len(converted_tracks)} tracks")
        return converted_tracks
    
    def transfer(self, 
                tracks: List[Tuple[TrackInfo, str]], 
                mount_point: Optional[str] = None) -> int:
        """
        Transfer tracks to iPod
        
        Args:
            tracks: List of (TrackInfo, path) tuples
            mount_point: iPod mount point (optional)
            
        Returns:
            Number of tracks transferred
        """
        logger.info("Transferring tracks to iPod")
        
        # Initialize iPod device
        self.ipod_device = IPodDevice(mount_point=mount_point)
        
        # If no mount point specified, try to detect and mount
        if not mount_point:
            logger.info("No mount point specified, attempting to detect iPod")
            
            devices = self.ipod_device.detect_devices()
            if not devices:
                logger.error("No iPod devices found")
                return 0
                
            logger.info(f"Found iPod: {devices[0]['name']} ({devices[0]['model']})")
            
            mount_point = self.ipod_device.mount_device(devices[0]['id'])
            if not mount_point:
                logger.error(f"Failed to mount iPod: {devices[0]['name']}")
                return 0
                
            logger.info(f"Mounted iPod at: {mount_point}")
        
        # Get device info
        device_info = self.ipod_device.get_device_info()
        free_space = device_info.get("free_space", 0)
        
        # Calculate total size of tracks
        total_size = 0
        for _, path in tracks:
            if os.path.exists(path):
                total_size += os.path.getsize(path)
        
        # Check if there's enough space
        if total_size > free_space:
            logger.error(
                f"Not enough space on iPod. Need {total_size / 1024**2:.1f} MB, " +
                f"but only {free_space / 1024**2:.1f} MB available"
            )
            return 0
        
        # Transfer each track
        transferred_count = 0
        for track, path in tqdm(tracks, desc="Transferring", unit="track"):
            if os.path.exists(path):
                # Transfer file
                success = self.ipod_device.transfer_file(path)
                if success:
                    transferred_count += 1
        
        logger.info(f"Transferred {transferred_count} tracks to iPod")
        return transferred_count
    
    def clean_temp_files(self):
        """Clean temporary files"""
        logger.info("Cleaning temporary files")
        
        # Remove all files in temp directory
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                logger.error(f"Error deleting {file_path}: {e}")
    
    def run(self):
        """Run the CLI"""
        # Parse arguments
        args = self.parse_arguments()
        
        try:
            # Download step
            if not args.skip_download:
                self.downloaded_tracks = self.download(
                    args.url, 
                    args.format, 
                    args.quality, 
                    args.video
                )
            else:
                logger.info("Skipping download step")
                # TODO: Load previously downloaded tracks
            
            # Convert step
            if not args.skip_convert:
                self.converted_tracks = self.convert(
                    self.downloaded_tracks,
                    args.output_dir,
                    args.format,
                    args.quality,
                    args.video,
                    args.resolution
                )
            else:
                logger.info("Skipping conversion step")
                # TODO: Load previously converted tracks
            
            # Transfer step
            if not args.skip_transfer:
                transferred_count = self.transfer(
                    self.converted_tracks,
                    args.device
                )
                
                if transferred_count > 0:
                    logger.info(f"Successfully transferred {transferred_count} tracks to iPod")
                else:
                    logger.error("Failed to transfer tracks to iPod")
            else:
                logger.info("Skipping transfer step")
            
            # Clean temp files
            if args.clean_temp:
                self.clean_temp_files()
            
            return 0
            
        except Exception as e:
            logger.exception(f"Error: {e}")
            return 1


if __name__ == "__main__":
    cli = YouTubeToIPodCLI()
    sys.exit(cli.run())
