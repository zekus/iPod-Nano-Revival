#!/usr/bin/env python3
"""
Setup script for YouTube Music to iPod Nano Transfer Tool
"""

from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Read long description from README.md
with open('README.md', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="youtube-to-ipod-nano",
    version="1.0.0",
    description="Transfer YouTube music/playlists directly to iPod Nano",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/youtube-to-ipod-nano",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'youtube-to-ipod=src.cli:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)
