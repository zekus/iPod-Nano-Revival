<!-- # YouTube Music to iPod Nano -->

An open-source Python tool that enables direct transfer of YouTube music/playlists to iPod Nano, bypassing iTunes. This application combines YouTube audio extraction, format conversion, metadata management, and direct device transfer while adhering to iPod Nano's technical specifications.

## Features

- Download audio from YouTube videos/playlists
- Convert to iPod-compatible formats (AAC/M4A)
- Automatic metadata handling (title, artist, album art)
- Direct transfer to iPod Nano
- Cross-platform support (Windows, macOS, Linux)

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/youtube-to-ipod-nano.git
cd youtube-to-ipod-nano
```

1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Install FFmpeg (required for audio conversion):
   - **macOS**: `brew install ffmpeg`
   - **Linux**: `sudo apt-get install ffmpeg`
   - **Windows**: Download from [FFmpeg website](https://ffmpeg.org/download.html)

## Usage

### GUI Application

Run the application:

```bash
python src/main.py
```

### Command Line Interface

```bash
python src/cli.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --output-dir "/path/to/ipod"
```

Options:

- `--url`: YouTube video or playlist URL
- `--output-dir`: Output directory (iPod mount point)
- `--format`: Audio format (default: m4a)
- `--quality`: Audio quality in kbps (default: 256)
- `--video`: Enable video download (for compatible iPod models)

## Legal Disclaimer

This tool is intended for personal use only. Users are responsible for complying with YouTube's Terms of Service and copyright laws. Please only download content that you have the right to access and use.

## License

MIT License
