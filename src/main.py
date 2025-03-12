#!/usr/bin/env python3
"""
Main Application Module for iPod Nano Transfer Tool
Provides a GUI for the YouTube Music to iPod Nano transfer tool
"""

import os
import sys
import logging
import threading
import time
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QProgressBar, QFileDialog,
    QComboBox, QCheckBox, QTabWidget, QListWidget, QListWidgetItem,
    QMessageBox, QSpinBox, QGroupBox, QRadioButton, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, pyqtSlot, QSize
from PyQt6.QtGui import QIcon, QPixmap

from youtube_downloader import YouTubeDownloader, TrackInfo
from audio_converter import AudioConverter
from metadata_handler import MetadataHandler
from ipod_device import IPodDevice

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    """Worker thread for background tasks"""
    
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str, object)
    
    def __init__(self, task_type: str, **kwargs):
        """
        Initialize worker thread
        
        Args:
            task_type: Type of task to perform
            **kwargs: Additional arguments for the task
        """
        super().__init__()
        self.task_type = task_type
        self.kwargs = kwargs
        self.is_running = True
    
    def run(self):
        """Run the worker thread"""
        try:
            if self.task_type == "download":
                self._run_download()
            elif self.task_type == "convert":
                self._run_convert()
            elif self.task_type == "transfer":
                self._run_transfer()
            elif self.task_type == "detect_devices":
                self._run_detect_devices()
            else:
                raise ValueError(f"Unknown task type: {self.task_type}")
                
        except Exception as e:
            logger.exception(f"Error in worker thread: {e}")
            self.finished_signal.emit(False, str(e), None)
    
    def _run_download(self):
        """Run download task"""
        url = self.kwargs.get("url")
        output_dir = self.kwargs.get("output_dir", "downloads")
        format = self.kwargs.get("format", "m4a")
        quality = self.kwargs.get("quality", 256)
        
        self.progress_signal.emit(0, f"Initializing download from {url}")
        
        # Initialize downloader with progress callback
        downloader = YouTubeDownloader(
            output_dir=output_dir,
            progress_callback=self._download_progress_callback
        )
        
        # Process URL
        tracks = downloader.process_url(url, format, quality)
        
        if not tracks:
            self.finished_signal.emit(False, "No tracks were successfully downloaded", [])
            return
            
        # Report success
        self.finished_signal.emit(True, f"Downloaded {len(tracks)} tracks", tracks)
    
    def _download_progress_callback(self, progress: int, status: str):
        """Callback for download progress updates"""
        self.progress_signal.emit(progress, status)
    
    def _run_convert(self):
        """Run conversion task"""
        tracks = self.kwargs.get("tracks", [])
        output_dir = self.kwargs.get("output_dir", "converted")
        format = self.kwargs.get("format", "m4a")
        quality = self.kwargs.get("quality", 256)
        
        # Filter out tracks without download paths
        valid_tracks = [track for track in tracks if hasattr(track, 'download_path') and track.download_path and os.path.exists(track.download_path)]
        
        if not valid_tracks:
            self.finished_signal.emit(False, "No valid tracks to convert", None)
            return
            
        self.progress_signal.emit(0, f"Initializing conversion of {len(valid_tracks)} tracks")
        
        # Initialize converter and metadata handler
        converter = AudioConverter(output_dir=output_dir)
        metadata_handler = MetadataHandler()
        
        # Convert each track
        converted_tracks = []
        for i, track in enumerate(valid_tracks):
            if not self.is_running:
                break
                
            progress = int((i / len(valid_tracks)) * 100)
            self.progress_signal.emit(progress, f"Converting {track.title}...")
            
            try:
                # Convert to iPod format
                output_path = converter.convert_to_ipod_format(
                    track, track.download_path, format, quality
                )
                
                # Embed metadata
                if output_path:
                    metadata_handler.process_file(output_path, track)
                    converted_tracks.append((track, output_path))
            except Exception as e:
                logger.error(f"Error converting track {track.title}: {e}")
                continue
        
        if not converted_tracks:
            self.finished_signal.emit(False, "Failed to convert any tracks", None)
            return
            
        # Report success
        self.finished_signal.emit(
            True, 
            f"Converted {len(converted_tracks)} tracks", 
            converted_tracks
        )
    
    def _run_transfer(self):
        """Run transfer task"""
        tracks = self.kwargs.get("tracks", [])
        mount_point = self.kwargs.get("mount_point")
        
        if not tracks:
            self.finished_signal.emit(False, "No tracks to transfer", None)
            return
            
        if not mount_point:
            self.finished_signal.emit(False, "No iPod device mounted", None)
            return
            
        self.progress_signal.emit(0, f"Initializing transfer of {len(tracks)} tracks")
        
        # Initialize iPod device
        ipod = IPodDevice(mount_point=mount_point)
        
        # Get device info
        device_info = ipod.get_device_info()
        free_space = device_info.get("free_space", 0)
        
        # Calculate total size of tracks
        total_size = 0
        for track, path in tracks:
            if os.path.exists(path):
                total_size += os.path.getsize(path)
        
        # Check if there's enough space
        if total_size > free_space:
            self.finished_signal.emit(
                False, 
                f"Not enough space on iPod. Need {total_size / 1024**2:.1f} MB, " +
                f"but only {free_space / 1024**2:.1f} MB available", 
                None
            )
            return
        
        # Transfer each track
        transferred_tracks = []
        for i, (track, path) in enumerate(tracks):
            if not self.is_running:
                break
                
            progress = int((i / len(tracks)) * 100)
            self.progress_signal.emit(progress, f"Transferring {track.title}...")
            
            if os.path.exists(path):
                # Transfer file
                success = ipod.transfer_file(path)
                if success:
                    transferred_tracks.append((track, path))
        
        # Report success
        self.finished_signal.emit(
            True, 
            f"Transferred {len(transferred_tracks)} tracks to iPod", 
            transferred_tracks
        )
    
    def _run_detect_devices(self):
        """Run device detection task"""
        self.progress_signal.emit(0, "Detecting iPod devices...")
        
        # Initialize iPod device
        ipod = IPodDevice()
        
        # Detect devices
        devices = ipod.detect_devices()
        
        if not devices:
            self.finished_signal.emit(False, "No iPod devices found", [])
            return
            
        # Report success
        self.finished_signal.emit(True, f"Found {len(devices)} iPod devices", devices)
    
    def stop(self):
        """Stop the worker thread"""
        self.is_running = False


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        """Initialize the main window"""
        super().__init__()
        
        self.setWindowTitle("YouTube to iPod Nano")
        self.setMinimumSize(800, 600)
        
        # Initialize variables
        self.worker_thread = None
        self.downloaded_tracks = []
        self.converted_tracks = []
        self.ipod_devices = []
        self.current_mount_point = None
        
        # Set up UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the user interface"""
        # Main widget and layout
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        
        # Tab widget
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)
        
        # Download tab
        download_tab = QWidget()
        tab_widget.addTab(download_tab, "Download")
        self._setup_download_tab(download_tab)
        
        # Convert tab
        convert_tab = QWidget()
        tab_widget.addTab(convert_tab, "Convert")
        self._setup_convert_tab(convert_tab)
        
        # Transfer tab
        transfer_tab = QWidget()
        tab_widget.addTab(transfer_tab, "Transfer")
        self._setup_transfer_tab(transfer_tab)
        
        # Settings tab
        settings_tab = QWidget()
        tab_widget.addTab(settings_tab, "Settings")
        self._setup_settings_tab(settings_tab)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Set central widget
        self.setCentralWidget(main_widget)
    
    def _setup_download_tab(self, tab):
        """Set up the download tab"""
        layout = QVBoxLayout(tab)
        
        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel("YouTube URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(["m4a", "mp3"])
        quality_label = QLabel("Quality (kbps):")
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(128, 320)
        self.quality_spin.setValue(256)
        self.quality_spin.setSingleStep(32)
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        format_layout.addWidget(quality_label)
        format_layout.addWidget(self.quality_spin)
        format_layout.addStretch()
        layout.addLayout(format_layout)
        
        # Download button
        self.download_button = QPushButton("Download")
        self.download_button.clicked.connect(self._on_download_clicked)
        layout.addWidget(self.download_button)
        
        # Progress bar
        self.download_progress = QProgressBar()
        self.download_progress.setRange(0, 100)
        self.download_progress.setValue(0)
        layout.addWidget(self.download_progress)
        
        # Status label
        self.download_status = QLabel("Ready to download")
        layout.addWidget(self.download_status)
        
        # Track list
        track_list_label = QLabel("Downloaded Tracks:")
        layout.addWidget(track_list_label)
        
        self.track_list = QListWidget()
        layout.addWidget(self.track_list)
    
    def _setup_convert_tab(self, tab):
        """Set up the convert tab"""
        layout = QVBoxLayout(tab)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Directory:")
        self.output_dir_input = QLineEdit()
        self.output_dir_input.setText(os.path.join(os.path.expanduser("~"), "Music", "iPod"))
        browse_button = QPushButton("Browse...")
        browse_button.clicked.connect(self._on_browse_output_clicked)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_dir_input)
        output_layout.addWidget(browse_button)
        layout.addLayout(output_layout)
        
        # Convert button
        self.convert_button = QPushButton("Convert Downloaded Tracks")
        self.convert_button.clicked.connect(self._on_convert_clicked)
        layout.addWidget(self.convert_button)
        
        # Progress bar
        self.convert_progress = QProgressBar()
        self.convert_progress.setRange(0, 100)
        self.convert_progress.setValue(0)
        layout.addWidget(self.convert_progress)
        
        # Status label
        self.convert_status = QLabel("Ready to convert")
        layout.addWidget(self.convert_status)
        
        # Converted track list
        converted_list_label = QLabel("Converted Tracks:")
        layout.addWidget(converted_list_label)
        
        self.converted_list = QListWidget()
        layout.addWidget(self.converted_list)
    
    def _setup_transfer_tab(self, tab):
        """Set up the transfer tab"""
        layout = QVBoxLayout(tab)
        
        # Device selection
        device_layout = QHBoxLayout()
        device_label = QLabel("iPod Device:")
        self.device_combo = QComboBox()
        self.device_combo.setPlaceholderText("No devices found")
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._on_refresh_devices_clicked)
        device_layout.addWidget(device_label)
        device_layout.addWidget(self.device_combo)
        device_layout.addWidget(refresh_button)
        layout.addLayout(device_layout)
        
        # Device info
        self.device_info_label = QLabel("No device selected")
        layout.addWidget(self.device_info_label)
        
        # Transfer button
        self.transfer_button = QPushButton("Transfer to iPod")
        self.transfer_button.clicked.connect(self._on_transfer_clicked)
        layout.addWidget(self.transfer_button)
        
        # Progress bar
        self.transfer_progress = QProgressBar()
        self.transfer_progress.setRange(0, 100)
        self.transfer_progress.setValue(0)
        layout.addWidget(self.transfer_progress)
        
        # Status label
        self.transfer_status = QLabel("Ready to transfer")
        layout.addWidget(self.transfer_status)
        
        # Transferred track list
        transferred_list_label = QLabel("Transferred Tracks:")
        layout.addWidget(transferred_list_label)
        
        self.transferred_list = QListWidget()
        layout.addWidget(self.transferred_list)
    
    def _setup_settings_tab(self, tab):
        """Set up the settings tab"""
        layout = QVBoxLayout(tab)
        
        # Video support
        video_group = QGroupBox("Video Support")
        video_layout = QVBoxLayout(video_group)
        
        self.enable_video_check = QCheckBox("Enable Video Download (iPod Nano 5th-7th gen)")
        video_layout.addWidget(self.enable_video_check)
        
        video_resolution_layout = QHBoxLayout()
        video_resolution_label = QLabel("Video Resolution:")
        self.video_resolution_combo = QComboBox()
        self.video_resolution_combo.addItems(["640x480", "480x360", "320x240"])
        self.video_resolution_combo.setEnabled(False)
        self.enable_video_check.toggled.connect(self.video_resolution_combo.setEnabled)
        
        video_resolution_layout.addWidget(video_resolution_label)
        video_resolution_layout.addWidget(self.video_resolution_combo)
        video_resolution_layout.addStretch()
        video_layout.addLayout(video_resolution_layout)
        
        layout.addWidget(video_group)
        
        # Metadata options
        metadata_group = QGroupBox("Metadata Options")
        metadata_layout = QVBoxLayout(metadata_group)
        
        self.embed_artwork_check = QCheckBox("Embed Album Artwork")
        self.embed_artwork_check.setChecked(True)
        metadata_layout.addWidget(self.embed_artwork_check)
        
        self.use_musicbrainz_check = QCheckBox("Use MusicBrainz for Enhanced Metadata (Experimental)")
        metadata_layout.addWidget(self.use_musicbrainz_check)
        
        layout.addWidget(metadata_group)
        
        # Advanced options
        advanced_group = QGroupBox("Advanced Options")
        advanced_layout = QVBoxLayout(advanced_group)
        
        self.clean_temp_check = QCheckBox("Clean Temporary Files After Transfer")
        self.clean_temp_check.setChecked(True)
        advanced_layout.addWidget(self.clean_temp_check)
        
        self.auto_detect_check = QCheckBox("Auto-Detect iPod on Startup")
        self.auto_detect_check.setChecked(True)
        advanced_layout.addWidget(self.auto_detect_check)
        
        layout.addWidget(advanced_group)
        
        # Spacer
        layout.addStretch()
        
        # About section
        about_label = QLabel(
            "YouTube to iPod Nano Transfer Tool\n"
            "Version 1.0.0\n\n"
            "An open-source Python tool that enables direct transfer of YouTube music/playlists to iPod Nano."
        )
        about_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(about_label)
    
    def _on_browse_output_clicked(self):
        """Handle browse output directory button click"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory", self.output_dir_input.text()
        )
        
        if directory:
            self.output_dir_input.setText(directory)
    
    def _on_download_clicked(self):
        """Handle download button click"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a YouTube URL")
            return
            
        if not (url.startswith("http://") or url.startswith("https://")):
            QMessageBox.warning(self, "Error", "Please enter a valid URL")
            return
            
        # Disable download button
        self.download_button.setEnabled(False)
        self.download_status.setText("Downloading...")
        self.download_progress.setValue(0)
        
        # Clear track list
        self.track_list.clear()
        
        # Start worker thread
        self.worker_thread = WorkerThread(
            task_type="download",
            url=url,
            format=self.format_combo.currentText(),
            quality=self.quality_spin.value()
        )
        
        self.worker_thread.progress_signal.connect(self._on_download_progress)
        self.worker_thread.finished_signal.connect(self._on_download_finished)
        self.worker_thread.start()
    
    def _on_download_progress(self, progress, status):
        """Handle download progress updates"""
        self.download_progress.setValue(progress)
        self.download_status.setText(status)
    
    def _on_download_finished(self, success, message, result):
        """Handle download completion"""
        # Enable download button
        self.download_button.setEnabled(True)
        
        if success and result:
            self.download_status.setText(message)
            self.downloaded_tracks = result
            
            # Update track list
            self.track_list.clear()
            for track in self.downloaded_tracks:
                if hasattr(track, 'download_path') and track.download_path:
                    item = QListWidgetItem(f"{track.artist} - {track.title}")
                    self.track_list.addItem(item)
            
            # Enable convert button if we have tracks
            if self.track_list.count() > 0:
                self.convert_button.setEnabled(True)
            else:
                self.convert_button.setEnabled(False)
                self.download_status.setText("No valid tracks were downloaded")
        else:
            self.download_status.setText(f"Error: {message}")
            QMessageBox.warning(self, "Download Error", message)
            self.downloaded_tracks = []
            self.track_list.clear()
        
        # Clean up worker thread
        self.worker_thread = None
    
    def _on_convert_clicked(self):
        """Handle convert button click"""
        if not self.downloaded_tracks:
            QMessageBox.warning(self, "Error", "No tracks to convert. Download tracks first.")
            return
            
        output_dir = self.output_dir_input.text().strip()
        
        if not output_dir:
            QMessageBox.warning(self, "Error", "Please enter an output directory")
            return
            
        # Disable convert button
        self.convert_button.setEnabled(False)
        self.convert_status.setText("Converting...")
        self.convert_progress.setValue(0)
        
        # Clear converted list
        self.converted_list.clear()
        
        # Start worker thread
        self.worker_thread = WorkerThread(
            task_type="convert",
            tracks=self.downloaded_tracks,
            output_dir=output_dir,
            format=self.format_combo.currentText(),
            quality=self.quality_spin.value()
        )
        
        self.worker_thread.progress_signal.connect(self._on_convert_progress)
        self.worker_thread.finished_signal.connect(self._on_convert_finished)
        self.worker_thread.start()
    
    def _on_convert_progress(self, progress, status):
        """Handle convert progress updates"""
        self.convert_progress.setValue(progress)
        self.convert_status.setText(status)
    
    def _on_convert_finished(self, success, message, result):
        """Handle convert completion"""
        # Enable convert button
        self.convert_button.setEnabled(True)
        
        if success:
            self.convert_status.setText(message)
            self.converted_tracks = result
            
            # Update converted list
            for track, path in self.converted_tracks:
                item = QListWidgetItem(f"{track.artist} - {track.title}")
                self.converted_list.addItem(item)
        else:
            self.convert_status.setText(f"Error: {message}")
            QMessageBox.warning(self, "Conversion Error", message)
        
        # Clean up worker thread
        self.worker_thread = None
    
    def _on_refresh_devices_clicked(self):
        """Handle refresh devices button click"""
        # Disable refresh button
        self.device_combo.clear()
        self.device_info_label.setText("Detecting devices...")
        
        # Start worker thread
        self.worker_thread = WorkerThread(task_type="detect_devices")
        
        self.worker_thread.progress_signal.connect(self._on_device_detection_progress)
        self.worker_thread.finished_signal.connect(self._on_device_detection_finished)
        self.worker_thread.start()
    
    def _on_device_detection_progress(self, progress, status):
        """Handle device detection progress updates"""
        self.device_info_label.setText(status)
    
    def _on_device_detection_finished(self, success, message, result):
        """Handle device detection completion"""
        if success:
            self.ipod_devices = result
            
            # Update device combo box
            self.device_combo.clear()
            for device in self.ipod_devices:
                self.device_combo.addItem(device.get("name", "Unknown Device"))
            
            # Try to mount the first device
            if self.ipod_devices:
                device_id = self.ipod_devices[0]["id"]
                ipod = IPodDevice()
                mount_point = ipod.mount_device(device_id)
                
                if mount_point:
                    # Get device info
                    self.current_mount_point = mount_point
                    device_info = ipod.get_device_info()
                    self.ipod_devices[0]["mount_point"] = mount_point
                    self.ipod_devices[0]["info"] = device_info
                    
                    # Update device info label
                    free_space = device_info.get("free_space", 0)
                    total_space = device_info.get("total_space", 0)
                    
                    self.device_info_label.setText(
                        f"Device: {self.ipod_devices[0]['name']}\n"
                        f"Mount Point: {mount_point}\n"
                        f"Free Space: {free_space / 1024**2:.1f} MB / {total_space / 1024**2:.1f} MB"
                    )
                    
                    # Enable transfer button
                    self.transfer_button.setEnabled(True)
                else:
                    self.device_info_label.setText(
                        f"Device: {self.ipod_devices[0]['name']}\n"
                        f"Failed to mount device. Please check permissions."
                    )
                    self.transfer_button.setEnabled(False)
            
            self.statusBar().showMessage(message)
        else:
            self.device_info_label.setText("No iPod devices found")
            self.device_combo.clear()
            self.transfer_button.setEnabled(False)
            self.statusBar().showMessage(message)
        
        # Clean up worker thread
        self.worker_thread = None
    
    def _on_transfer_clicked(self):
        """Handle transfer button click"""
        if not self.converted_tracks:
            QMessageBox.warning(self, "Error", "No tracks to transfer. Convert tracks first.")
            return
            
        if not self.current_mount_point:
            QMessageBox.warning(self, "Error", "No iPod device mounted. Refresh devices first.")
            return
            
        # Disable transfer button
        self.transfer_button.setEnabled(False)
        self.transfer_status.setText("Transferring...")
        self.transfer_progress.setValue(0)
        
        # Clear transferred list
        self.transferred_list.clear()
        
        # Start worker thread
        self.worker_thread = WorkerThread(
            task_type="transfer",
            tracks=self.converted_tracks,
            mount_point=self.current_mount_point
        )
        
        self.worker_thread.progress_signal.connect(self._on_transfer_progress)
        self.worker_thread.finished_signal.connect(self._on_transfer_finished)
        self.worker_thread.start()
    
    def _on_transfer_progress(self, progress, status):
        """Handle transfer progress updates"""
        self.transfer_progress.setValue(progress)
        self.transfer_status.setText(status)
    
    def _on_transfer_finished(self, success, message, result):
        """Handle transfer completion"""
        # Enable transfer button
        self.transfer_button.setEnabled(True)
        
        if success:
            self.transfer_status.setText(message)
            
            # Update transferred list
            for track, path in result:
                item = QListWidgetItem(f"{track.artist} - {track.title}")
                self.transferred_list.addItem(item)
                
            QMessageBox.information(self, "Transfer Complete", message)
        else:
            self.transfer_status.setText(f"Error: {message}")
            QMessageBox.warning(self, "Transfer Error", message)
        
        # Clean up worker thread
        self.worker_thread = None
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Stop worker thread if running
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait()
        
        # Accept close event
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
