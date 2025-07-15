"""
Configuration module for the Media Generation Pipeline.
Handles API keys, settings, and environment variables.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class APIConfig:
    """Configuration for API credentials and settings."""
    
    # API Keys - Should be set via environment variables
    openai_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None
    
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
    
    def __post_init__(self):
        """Load API keys from environment variables if not provided."""
        if not self.openai_api_key:
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.stability_api_key:
            self.stability_api_key = os.getenv('STABILITY_API_KEY')
    
    def validate(self) -> bool:
        """Validate that required API keys are present."""
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        if not self.stability_api_key:
            raise ValueError("Stability AI API key is required. Set STABILITY_API_KEY environment variable.")
        return True

# Default configuration instance
config = APIConfig() 