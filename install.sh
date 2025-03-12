#!/bin/bash
# Installation script for YouTube Music to iPod Nano Transfer Tool

set -e

echo "Installing YouTube Music to iPod Nano Transfer Tool..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed. Please install Python 3 and try again."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is required but not installed. Please install pip3 and try again."
    exit 1
fi

# Check if FFmpeg is installed
if ! command -v ffmpeg &> /dev/null; then
    echo "FFmpeg is required but not installed."
    echo "Please install FFmpeg:"
    echo "  - macOS: brew install ffmpeg"
    echo "  - Linux: sudo apt-get install ffmpeg"
    echo "  - Windows: Download from https://ffmpeg.org/download.html"
    exit 1
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p temp downloads converted

echo ""
echo "Installation complete!"
echo ""
echo "To run the application:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Run the GUI application: python run.py"
echo "  3. Or run the CLI application: python run.py --cli --url \"https://www.youtube.com/watch?v=VIDEO_ID\""
echo ""
echo "For more information, see the README.md file."
