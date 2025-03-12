#!/usr/bin/env python3
"""
Launcher script for YouTube Music to iPod Nano Transfer Tool
"""

import os
import sys
import argparse

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="YouTube to iPod Nano Transfer Tool")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode")
    args = parser.parse_args()
    
    # Add src directory to path
    src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "src")
    sys.path.insert(0, src_dir)
    
    if args.cli:
        # Run CLI version
        from src.cli import YouTubeToIPodCLI
        cli = YouTubeToIPodCLI()
        return cli.run()
    else:
        # Run GUI version
        from src.main import QApplication, MainWindow
        app = QApplication(sys.argv)
        window = MainWindow()
        window.show()
        return app.exec()

if __name__ == "__main__":
    sys.exit(main())
