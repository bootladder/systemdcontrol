#!/usr/bin/env python3

from pathlib import Path
from setuptools import setup, find_packages

readme_file = Path(__file__).parent / "readme.txt"
long_description = readme_file.read_text() if readme_file.exists() else ""

setup(
    name="systemdcontrol",
    version="1.0.0",
    description="User-friendly systemd service control tool with CLI and TUI interfaces",
    long_description=long_description,
    long_description_content_type="text/plain",
    author="SystemD Control",
    python_requires=">=3.6",
    py_modules=["systemdcontrol", "systemdcontrol_tui"],
    entry_points={
        "console_scripts": [
            "systemdcontrol=systemdcontrol:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Console :: Curses",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
    ],
    keywords="systemd systemctl service management linux archlinux tui cli",
    install_requires=[],
    extras_require={
        "dev": ["pytest", "black", "flake8"],
    },
)