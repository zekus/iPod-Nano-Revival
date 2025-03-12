#!/usr/bin/env python3
"""
iPod Device Handler Module for iPod Nano Transfer Tool
Handles device detection and file transfer to iPod Nano
"""

import os
import sys
import logging
import platform
import shutil
import subprocess
from typing import List, Dict, Optional, Tuple, Any
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IPodDevice:
    """Class to handle iPod device detection and file transfer"""
    
    def __init__(self, mount_point: Optional[str] = None):
        """
        Initialize the iPod device handler
        
        Args:
            mount_point: Path to iPod mount point (optional)
        """
        self.mount_point = mount_point
        self.system = platform.system()
        self.device_info = {}
        self.logger = logger  # Add this line
        
        # Check if libimobiledevice is installed
        if not self._check_dependencies():
            self.logger.warning("Some dependencies are missing. Device detection may not work properly.")
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed
        
        Returns:
            True if all dependencies are installed, False otherwise
        """
        try:
            if self.system == "Linux":
                # Check for ifuse and libimobiledevice
                subprocess.run(["which", "ifuse"], check=True, capture_output=True)
                subprocess.run(["which", "idevice_id"], check=True, capture_output=True)
                return True
            elif self.system == "Darwin":  # macOS
                # Check for libimobiledevice
                subprocess.run(["which", "idevice_id"], check=True, capture_output=True)
                return True
            elif self.system == "Windows":
                # Check for libimobiledevice-win32 (simplified check)
                # In reality, this would need a more complex check
                return os.path.exists("C:\\Program Files\\libimobiledevice")
            
            return False
        except subprocess.SubprocessError:
            return False
    
    def detect_devices(self) -> List[Dict[str, str]]:
        """
        Detect connected iPod devices
        
        Returns:
            List of dictionaries with device information
        """
        devices = []
        
        # Check platform
        system = platform.system()
        
        try:
            if system == "Darwin":  # macOS
                # Try using libimobiledevice if available
                try:
                    result = subprocess.run(
                        ["idevice_id", "-l"],
                        capture_output=True,
                        check=False,
                        text=True
                    )
                    
                    if result.returncode == 0 and result.stdout.strip():
                        # Parse device IDs
                        device_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                        
                        for device_id in device_ids:
                            # Get device info
                            info_result = subprocess.run(
                                ["ideviceinfo", "-u", device_id],
                                capture_output=True,
                                check=False,
                                text=True
                            )
                            
                            if info_result.returncode == 0:
                                # Parse device info
                                device_info = {}
                                for line in info_result.stdout.splitlines():
                                    if ":" in line:
                                        key, value = line.split(":", 1)
                                        device_info[key.strip()] = value.strip()
                                
                                if "ProductType" in device_info and "iPod" in device_info["ProductType"]:
                                    devices.append({
                                        "id": device_id,
                                        "name": device_info.get("DeviceName", "iPod"),
                                        "model": device_info.get("ProductType", "Unknown"),
                                        "mount_point": self._get_ipod_mount_point(device_id)
                                    })
                except FileNotFoundError:
                    # libimobiledevice not installed, fall back to disk utility
                    self.logger.warning("libimobiledevice not found, falling back to disk utility")
                    
                # Fall back to diskutil list
                result = subprocess.run(
                    ["diskutil", "list"],
                    capture_output=True,
                    check=False,
                    text=True
                )
                
                if result.returncode == 0:
                    # Look for iPod in the output
                    for line in result.stdout.splitlines():
                        if "iPod" in line:
                            # Extract disk identifier
                            parts = line.split()
                            for i, part in enumerate(parts):
                                if part.startswith("/dev/"):
                                    disk_id = part
                                    
                                    # Get mount point
                                    mount_result = subprocess.run(
                                        ["diskutil", "info", disk_id],
                                        capture_output=True,
                                        check=False,
                                        text=True
                                    )
                                    
                                    if mount_result.returncode == 0:
                                        mount_point = None
                                        for info_line in mount_result.stdout.splitlines():
                                            if "Mount Point" in info_line:
                                                mount_point = info_line.split(":", 1)[1].strip()
                                                break
                                        
                                        if mount_point and os.path.exists(mount_point):
                                            devices.append({
                                                "id": disk_id,
                                                "name": "iPod",
                                                "model": "Unknown",
                                                "mount_point": mount_point
                                            })
                
                # If no devices found, check for mounted volumes with iPod in the name
                if not devices:
                    volumes_dir = "/Volumes"
                    if os.path.exists(volumes_dir):
                        for volume in os.listdir(volumes_dir):
                            volume_path = os.path.join(volumes_dir, volume)
                            if "iPod" in volume and os.path.isdir(volume_path):
                                devices.append({
                                    "id": "unknown",
                                    "name": volume,
                                    "model": "Unknown",
                                    "mount_point": volume_path
                                })
                
            elif system == "Windows":
                # On Windows, check for mounted drives with iPod in the label
                import win32api
                import win32con
                
                try:
                    drives = win32api.GetLogicalDriveStrings().split('\0')[:-1]
                    for drive in drives:
                        try:
                            volume_name = win32api.GetVolumeInformation(drive)[0]
                            if volume_name and "iPod" in volume_name:
                                devices.append({
                                    "id": drive[0],
                                    "name": volume_name,
                                    "model": "Unknown",
                                    "mount_point": drive
                                })
                        except:
                            pass
                except ImportError:
                    self.logger.warning("win32api module not available, cannot detect iPod on Windows")
                    
                    # Fallback to checking drive letters
                    import string
                    for letter in string.ascii_uppercase:
                        drive = f"{letter}:\\"
                        if os.path.exists(drive):
                            # Check if this looks like an iPod
                            if os.path.exists(os.path.join(drive, "iPod_Control")):
                                devices.append({
                                    "id": letter,
                                    "name": "iPod",
                                    "model": "Unknown",
                                    "mount_point": drive
                                })
            
            elif system == "Linux":
                # On Linux, check mounted devices
                try:
                    result = subprocess.run(
                        ["lsblk", "-o", "NAME,LABEL,MOUNTPOINT", "-J"],
                        capture_output=True,
                        check=False,
                        text=True
                    )
                    
                    if result.returncode == 0:
                        import json
                        try:
                            data = json.loads(result.stdout)
                            for device in data.get("blockdevices", []):
                                if "children" in device:
                                    for child in device["children"]:
                                        label = child.get("label", "")
                                        mountpoint = child.get("mountpoint")
                                        if mountpoint and label and "iPod" in label:
                                            devices.append({
                                                "id": child.get("name", "unknown"),
                                                "name": label,
                                                "model": "Unknown",
                                                "mount_point": mountpoint
                                            })
                        except json.JSONDecodeError:
                            self.logger.warning("Failed to parse lsblk output as JSON")
                except FileNotFoundError:
                    self.logger.warning("lsblk command not found")
                
                # Fallback to checking /media and /mnt directories
                if not devices:
                    for mount_dir in ["/media", "/mnt"]:
                        if os.path.exists(mount_dir):
                            for user_dir in os.listdir(mount_dir):
                                user_path = os.path.join(mount_dir, user_dir)
                                if os.path.isdir(user_path):
                                    for device_dir in os.listdir(user_path):
                                        if "iPod" in device_dir:
                                            device_path = os.path.join(user_path, device_dir)
                                            if os.path.isdir(device_path):
                                                devices.append({
                                                    "id": "unknown",
                                                    "name": device_dir,
                                                    "model": "Unknown",
                                                    "mount_point": device_path
                                                })
        except Exception as e:
            self.logger.error(f"Error detecting devices: {e}")
            
        # If no devices found through system methods, check for manual mount point
        if not devices and self.mount_point and os.path.exists(self.mount_point):
            devices.append({
                "id": "manual",
                "name": os.path.basename(self.mount_point),
                "model": "Unknown",
                "mount_point": self.mount_point
            })
            
        return devices
    
    def _get_ipod_mount_point(self, device_id: str) -> Optional[str]:
        """
        Get the mount point for an iPod device
        
        Args:
            device_id: Device ID
        
        Returns:
            Mount point if found, None otherwise
        """
        # This method is not implemented in the provided code
        # You may need to implement it according to your requirements
        pass
    
    def mount_device(self, device_id: Optional[str] = None) -> Optional[str]:
        """
        Mount iPod device
        
        Args:
            device_id: Device ID (optional)
            
        Returns:
            Mount point if successful, None otherwise
        """
        if self.mount_point and os.path.exists(self.mount_point):
            self.logger.info(f"Device already mounted at: {self.mount_point}")
            return self.mount_point
            
        try:
            if self.system == "Linux":
                # Create mount point
                mount_point = "/tmp/ipod_mount"
                os.makedirs(mount_point, exist_ok=True)
                
                # Mount with ifuse
                cmd = ["ifuse", mount_point]
                if device_id:
                    cmd.extend(["-u", device_id])
                    
                subprocess.run(cmd, check=True)
                
                self.mount_point = mount_point
                self.logger.info(f"Device mounted at: {mount_point}")
                return mount_point
                
            elif self.system == "Darwin":
                # On macOS, devices are automatically mounted
                # Find the iPod mount point
                result = subprocess.run(
                    ["df", "-h"], 
                    check=True, 
                    capture_output=True, 
                    text=True
                )
                
                for line in result.stdout.strip().split('\n'):
                    if "iPod" in line:
                        # Extract disk identifier
                        parts = line.split()
                        if len(parts) >= 9:  # macOS df output format
                            mount_point = parts[8]
                            self.mount_point = mount_point
                            self.logger.info(f"Device found at: {mount_point}")
                            return mount_point
                
                self.logger.warning("iPod mount point not found")
                return None
                
            elif self.system == "Windows":
                # Windows implementation would go here
                # This is a placeholder for future implementation
                self.logger.warning("Windows mounting not fully implemented")
                return None
                
        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to mount device: {e}")
            return None
    
    def unmount_device(self) -> bool:
        """
        Unmount iPod device
        
        Returns:
            True if successful, False otherwise
        """
        if not self.mount_point:
            self.logger.warning("No device mounted")
            return False
            
        try:
            if self.system == "Linux":
                # Unmount with fusermount
                subprocess.run(["fusermount", "-u", self.mount_point], check=True)
                self.logger.info(f"Device unmounted: {self.mount_point}")
                self.mount_point = None
                return True
                
            elif self.system == "Darwin":
                # On macOS, use diskutil
                subprocess.run(["diskutil", "eject", self.mount_point], check=True)
                self.logger.info(f"Device ejected: {self.mount_point}")
                self.mount_point = None
                return True
                
            elif self.system == "Windows":
                # Windows implementation would go here
                # This is a placeholder for future implementation
                self.logger.warning("Windows unmounting not fully implemented")
                return False
                
        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to unmount device: {e}")
            return False
    
    def get_device_info(self) -> Dict[str, Any]:
        """
        Get information about the mounted device
        
        Returns:
            Dictionary with device information
        """
        if not self.mount_point or not os.path.exists(self.mount_point):
            self.logger.warning("No device mounted")
            return {}
            
        info = {
            "mount_point": self.mount_point,
            "total_space": 0,
            "free_space": 0,
            "used_space": 0
        }
        
        try:
            # Get disk usage
            usage = shutil.disk_usage(self.mount_point)
            info["total_space"] = usage.total
            info["free_space"] = usage.free
            info["used_space"] = usage.used
            
            # Check for iPod directory structure
            music_dir = os.path.join(self.mount_point, "Music")
            if os.path.exists(music_dir):
                info["has_music_dir"] = True
                
                # Count music files
                music_files = []
                for root, _, files in os.walk(music_dir):
                    for file in files:
                        if file.lower().endswith(('.m4a', '.mp3', '.aac')):
                            music_files.append(os.path.join(root, file))
                
                info["music_file_count"] = len(music_files)
            else:
                info["has_music_dir"] = False
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get device info: {e}")
            return info
    
    def transfer_file(self, source_file: str, relative_path: Optional[str] = None) -> bool:
        """
        Transfer file to iPod device
        
        Args:
            source_file: Path to source file
            relative_path: Relative path on iPod (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.mount_point or not os.path.exists(self.mount_point):
            self.logger.warning("No device mounted")
            return False
            
        if not os.path.exists(source_file):
            self.logger.warning(f"Source file does not exist: {source_file}")
            return False
            
        try:
            # Determine destination path
            if relative_path:
                dest_dir = os.path.join(self.mount_point, relative_path)
            else:
                # Default to Music directory
                dest_dir = os.path.join(self.mount_point, "Music")
                
                # Extract artist and album from source path
                parts = Path(source_file).parts
                if len(parts) >= 3:
                    artist = parts[-3]
                    album = parts[-2]
                    dest_dir = os.path.join(self.mount_point, "Music", artist, album)
            
            # Create destination directory if it doesn't exist
            os.makedirs(dest_dir, exist_ok=True)
            
            # Copy file
            filename = os.path.basename(source_file)
            dest_file = os.path.join(dest_dir, filename)
            
            shutil.copy2(source_file, dest_file)
            self.logger.info(f"File transferred: {dest_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to transfer file: {e}")
            return False
    
    def transfer_directory(self, source_dir: str, dest_dir: Optional[str] = None) -> bool:
        """
        Transfer directory to iPod device
        
        Args:
            source_dir: Path to source directory
            dest_dir: Destination directory on iPod (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.mount_point or not os.path.exists(self.mount_point):
            self.logger.warning("No device mounted")
            return False
            
        if not os.path.exists(source_dir) or not os.path.isdir(source_dir):
            self.logger.warning(f"Source directory does not exist: {source_dir}")
            return False
            
        try:
            # Determine destination path
            if dest_dir:
                full_dest_dir = os.path.join(self.mount_point, dest_dir)
            else:
                # Default to Music directory
                full_dest_dir = os.path.join(self.mount_point, "Music")
            
            # Create destination directory if it doesn't exist
            os.makedirs(full_dest_dir, exist_ok=True)
            
            # Copy directory contents
            for root, dirs, files in os.walk(source_dir):
                # Create relative path
                rel_path = os.path.relpath(root, source_dir)
                if rel_path == '.':
                    rel_path = ''
                
                # Create destination subdirectory
                dest_subdir = os.path.join(full_dest_dir, rel_path)
                os.makedirs(dest_subdir, exist_ok=True)
                
                # Copy files
                for file in files:
                    if file.lower().endswith(('.m4a', '.mp3', '.aac', '.mp4')):
                        src_file = os.path.join(root, file)
                        dst_file = os.path.join(dest_subdir, file)
                        shutil.copy2(src_file, dst_file)
                        self.logger.info(f"Transferred: {dst_file}")
            
            self.logger.info(f"Directory transferred: {source_dir} -> {full_dest_dir}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to transfer directory: {e}")
            return False


if __name__ == "__main__":
    # Example usage
    ipod = IPodDevice()
    
    # Detect devices
    devices = ipod.detect_devices()
    for device in devices:
        print(f"Found device: {device['name']} ({device['model']})")
    
    # Mount device
    if devices:
        mount_point = ipod.mount_device(devices[0]['id'])
        if mount_point:
            print(f"Device mounted at: {mount_point}")
            
            # Get device info
            info = ipod.get_device_info()
            print(f"Total space: {info.get('total_space', 0) / (1024**3):.2f} GB")
            print(f"Free space: {info.get('free_space', 0) / (1024**3):.2f} GB")
            
            # Unmount device
            ipod.unmount_device()
