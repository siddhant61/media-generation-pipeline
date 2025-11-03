"""
Configuration module for the Media Generation Pipeline.
Handles API keys, settings, and environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class LLMConfig:
    """Configuration for LLM-based scene generation."""
    scene_generation_model: str = "gpt-4o-mini"
    scene_generation_prompt: str = """You are a creative scene generator for video content. Given a topic, generate exactly {{num_scenes}} scenes that tell a coherent story.

For each scene, provide:
1. A descriptive name (short, catchy title)
2. A detailed image generation prompt (describe visual elements, style, mood)
3. A narration text (30-60 seconds of engaging spoken content)

Return your response as a JSON array with this structure:
[
  {{
    "name": "Scene Name",
    "prompt": "Detailed image generation prompt...",
    "narration": "Narration text for this scene..."
  }}
]

Topic: {{topic}}

Generate {{num_scenes}} scenes that create a compelling narrative."""

@dataclass
class TTSConfig:
    """Configuration for Text-to-Speech generation."""
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"
    audio_output_dir: str = "generated_content/audio"

@dataclass
class VideoConfig:
    """Configuration for video production settings."""
    background_music_file: Optional[str] = None
    background_music_volume: float = 0.1
    video_fps: int = 24
    ken_burns_enabled: bool = True
    ken_burns_zoom_ratio: float = 1.1
    subtitles_enabled: bool = True
    subtitle_font: str = "Arial"
    subtitle_fontsize: int = 24
    subtitle_color: str = "white"
    subtitle_bg_color: str = "black"
    subtitle_position: str = "bottom"

@dataclass
class APIConfig:
    """Configuration for API credentials and settings."""
    
    # API Keys - Should be set via environment variables
    openai_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None
    api_key: Optional[str] = None  # API key for protecting endpoints
    
    # OpenAI Settings
    openai_model: str = "gpt-4o-mini"
    max_tokens: int = 2000
    temperature: float = 0.7
    
    # Stability AI Settings
    stability_seed: int = 42
    stability_steps: int = 50
    stability_cfg_scale: float = 7.0
    stability_width: int = 512
    stability_height: int = 512
    stability_samples: int = 1
    
    # Output Settings
    output_dir: str = "generated_content"
    font_size: int = 40
    
    # Sub-configurations
    llm_config: LLMConfig = None
    tts_config: TTSConfig = None
    video_config: VideoConfig = None
    
    def __post_init__(self):
        """Load API keys from environment variables if not provided."""
        if not self.openai_api_key:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.stability_api_key:
            self.stability_api_key = os.getenv('STABILITY_API_KEY')
        if not self.api_key:
            self.api_key = os.getenv('API_KEY')
        
        # Initialize sub-configurations if not provided
        if self.llm_config is None:
            self.llm_config = LLMConfig()
        if self.tts_config is None:
            self.tts_config = TTSConfig()
        if self.video_config is None:
            self.video_config = VideoConfig()
            # Load background music from environment variable
            bg_music = os.getenv('BACKGROUND_MUSIC_FILE')
            if bg_music:
                self.video_config.background_music_file = bg_music
    
    def validate(self) -> bool:
        """Validate that required API keys are present."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        if not self.stability_api_key:
            raise ValueError("Stability AI API key is required. Set STABILITY_API_KEY environment variable.")
        return True

# Default configuration instance
config = APIConfig() 