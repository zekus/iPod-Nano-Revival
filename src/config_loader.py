#!/usr/bin/env python3
"""
Configuration Loader Module for iPod Nano Transfer Tool
Handles reading and writing configuration settings
"""

import os
import logging
import configparser
from pathlib import Path
from typing import Any, Dict, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ConfigLoader:
    """Class to handle configuration loading and saving"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize the configuration loader
        
        Args:
            config_file: Path to configuration file (optional)
        """
        # Default config file is in the project root directory
        if not config_file:
            self.config_file = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "config.ini"
            )
        else:
            self.config_file = config_file
            
        self.config = configparser.ConfigParser()
        
        # Load configuration
        self.load()
    
    def load(self) -> bool:
        """
        Load configuration from file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if os.path.exists(self.config_file):
                logger.info(f"Loading configuration from {self.config_file}")
                self.config.read(self.config_file)
                return True
            else:
                logger.warning(f"Configuration file {self.config_file} not found, using defaults")
                self._set_defaults()
                return False
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self._set_defaults()
            return False
    
    def save(self) -> bool:
        """
        Save configuration to file
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Saving configuration to {self.config_file}")
            
            with open(self.config_file, 'w') as f:
                self.config.write(f)
                
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            return False
    
    def _set_defaults(self):
        """Set default configuration values"""
        # General section
        if not self.config.has_section('General'):
            self.config.add_section('General')
            
        self.config.set('General', 'output_dir', os.path.join(os.path.expanduser("~"), "Music", "iPod"))
        self.config.set('General', 'format', 'm4a')
        self.config.set('General', 'quality', '256')
        self.config.set('General', 'clean_temp', 'true')
        
        # Video section
        if not self.config.has_section('Video'):
            self.config.add_section('Video')
            
        self.config.set('Video', 'enable_video', 'false')
        self.config.set('Video', 'resolution', '640x480')
        
        # Metadata section
        if not self.config.has_section('Metadata'):
            self.config.add_section('Metadata')
            
        self.config.set('Metadata', 'embed_artwork', 'true')
        self.config.set('Metadata', 'use_musicbrainz', 'false')
        
        # Device section
        if not self.config.has_section('Device'):
            self.config.add_section('Device')
            
        self.config.set('Device', 'auto_detect', 'true')
        self.config.set('Device', 'mount_point', '')
        
        # Advanced section
        if not self.config.has_section('Advanced'):
            self.config.add_section('Advanced')
            
        self.config.set('Advanced', 'temp_dir', 'temp')
        self.config.set('Advanced', 'concurrent_downloads', '2')
        self.config.set('Advanced', 'debug', 'false')
    
    def get(self, section: str, option: str, fallback: Any = None) -> Any:
        """
        Get configuration value
        
        Args:
            section: Configuration section
            option: Configuration option
            fallback: Fallback value if option not found
            
        Returns:
            Configuration value
        """
        try:
            return self.config.get(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_boolean(self, section: str, option: str, fallback: bool = False) -> bool:
        """
        Get boolean configuration value
        
        Args:
            section: Configuration section
            option: Configuration option
            fallback: Fallback value if option not found
            
        Returns:
            Boolean configuration value
        """
        try:
            return self.config.getboolean(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_int(self, section: str, option: str, fallback: int = 0) -> int:
        """
        Get integer configuration value
        
        Args:
            section: Configuration section
            option: Configuration option
            fallback: Fallback value if option not found
            
        Returns:
            Integer configuration value
        """
        try:
            return self.config.getint(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def get_float(self, section: str, option: str, fallback: float = 0.0) -> float:
        """
        Get float configuration value
        
        Args:
            section: Configuration section
            option: Configuration option
            fallback: Fallback value if option not found
            
        Returns:
            Float configuration value
        """
        try:
            return self.config.getfloat(section, option, fallback=fallback)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def set(self, section: str, option: str, value: Any) -> None:
        """
        Set configuration value
        
        Args:
            section: Configuration section
            option: Configuration option
            value: Configuration value
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
            
        self.config.set(section, option, str(value))
    
    def get_all(self) -> Dict[str, Dict[str, str]]:
        """
        Get all configuration values
        
        Returns:
            Dictionary of all configuration values
        """
        result = {}
        
        for section in self.config.sections():
            result[section] = {}
            
            for option in self.config.options(section):
                result[section][option] = self.config.get(section, option)
                
        return result


if __name__ == "__main__":
    # Example usage
    config = ConfigLoader()
    
    # Get configuration values
    output_dir = config.get('General', 'output_dir')
    format = config.get('General', 'format')
    quality = config.get_int('General', 'quality')
    
    print(f"Output directory: {output_dir}")
    print(f"Format: {format}")
    print(f"Quality: {quality} kbps")
    
    # Set configuration value
    config.set('General', 'format', 'mp3')
    
    # Save configuration
    config.save()
