#!/usr/bin/env python3
"""
Basic tests for YouTube Music to iPod Nano Transfer Tool
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from youtube_downloader import YouTubeDownloader, TrackInfo
from audio_converter import AudioConverter
from metadata_handler import MetadataHandler
from ipod_device import IPodDevice


class TestYouTubeDownloader(unittest.TestCase):
    """Test YouTube downloader functionality"""
    
    def test_parse_artist_title(self):
        """Test parsing artist and title from video title"""
        downloader = YouTubeDownloader()
        
        # Test case 1: Artist - Title
        artist, title = downloader._parse_artist_title("Rick Astley - Never Gonna Give You Up")
        self.assertEqual(artist, "Rick Astley")
        self.assertEqual(title, "Never Gonna Give You Up")
        
        # Test case 2: Artist: Title
        artist, title = downloader._parse_artist_title("Rick Astley: Never Gonna Give You Up")
        self.assertEqual(artist, "Rick Astley")
        self.assertEqual(title, "Never Gonna Give You Up")
        
        # Test case 3: Artist | Title
        artist, title = downloader._parse_artist_title("Rick Astley | Never Gonna Give You Up")
        self.assertEqual(artist, "Rick Astley")
        self.assertEqual(title, "Never Gonna Give You Up")
        
        # Test case 4: No pattern match
        artist, title = downloader._parse_artist_title("Never Gonna Give You Up")
        self.assertEqual(artist, "")
        self.assertEqual(title, "Never Gonna Give You Up")


class TestAudioConverter(unittest.TestCase):
    """Test audio converter functionality"""
    
    def test_sanitize_filename(self):
        """Test filename sanitization"""
        converter = AudioConverter()
        
        # Test case 1: Invalid characters
        sanitized = converter._sanitize_filename('File: with "invalid" chars?')
        self.assertEqual(sanitized, 'File_ with _invalid_ chars_')
        
        # Test case 2: Long filename
        long_name = "A" * 150
        sanitized = converter._sanitize_filename(long_name)
        self.assertEqual(len(sanitized), 100)
        self.assertTrue(sanitized.endswith('...'))


class TestMetadataHandler(unittest.TestCase):
    """Test metadata handler functionality"""
    
    @patch('requests.get')
    def test_download_thumbnail(self, mock_get):
        """Test thumbnail download"""
        # Mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'fake_image_data'
        mock_get.return_value = mock_response
        
        # Mock PIL Image
        with patch('PIL.Image.open') as mock_image_open:
            mock_image = MagicMock()
            mock_image.save.return_value = None
            mock_image_open.return_value = mock_image
            
            handler = MetadataHandler()
            result = handler.download_thumbnail("https://example.com/image.jpg")
            
            # Check that the function returned a path
            self.assertIsNotNone(result)
            mock_get.assert_called_once_with("https://example.com/image.jpg", timeout=10)


if __name__ == "__main__":
    unittest.main()
