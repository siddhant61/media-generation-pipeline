#!/usr/bin/env python3
"""
Setup script for the Media Generation Pipeline.
Standard setuptools configuration for package installation.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the long description from README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements from requirements.txt
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="media-generation-pipeline",
    version="2.0.0",
    author="Siddhant",
    description="AI-powered dynamic video generation pipeline with LLM-based scene generation and audio synthesis",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/siddhant61/media-generation-pipeline",
    packages=find_packages(exclude=["tests", "tests.*"]),
    py_modules=[
        "config",
        "scene_manager",
        "content_generator",
        "image_processor",
        "video_assembler",
        "main",
        "cli",
        "scene_plan_generator",
        "media_package_writer",
        "run_manifest_writer",
        "generate_scene_plan",
        "validate_artifacts",
    ],
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "media-pipeline=cli:main",
            "media-pipeline-api=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Topic :: Multimedia :: Video",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    keywords="video-generation ai llm openai stability-ai text-to-speech moviepy",
    project_urls={
        "Bug Reports": "https://github.com/siddhant61/media-generation-pipeline/issues",
        "Source": "https://github.com/siddhant61/media-generation-pipeline",
    },
) 