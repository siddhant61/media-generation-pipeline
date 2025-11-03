"""
Integration tests for the Media Generation Pipeline.
Tests the complete pipeline flow with mocked API calls.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
import json
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import APIConfig, LLMConfig, TTSConfig
from scene_manager import Scene, SceneManager
from content_generator import ContentGenerator
from main import MediaGenerationPipeline


@pytest.fixture
def mock_api_config():
    """Create a mock API configuration."""
    config = APIConfig(
        openai_api_key="test-openai-key",
        stability_api_key="test-stability-key",
        output_dir="/tmp/test_output"
    )
    return config


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    mock_client = Mock()
    
    # Mock chat completions for scene generation
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content=json.dumps([
        {
            "name": "Test Scene 1",
            "prompt": "A beautiful test scene",
            "narration": "This is a test narration for the first scene."
        },
        {
            "name": "Test Scene 2",
            "prompt": "Another test scene",
            "narration": "This is a test narration for the second scene."
        }
    ])))]
    mock_client.chat.completions.create.return_value = mock_response
    
    # Mock TTS audio generation
    mock_audio_response = Mock()
    mock_audio_response.stream_to_file = Mock()
    mock_client.audio.speech.create.return_value = mock_audio_response
    
    return mock_client


@pytest.fixture
def mock_stability_client():
    """Create a mock Stability AI client."""
    mock_client = Mock()
    
    # Mock image generation
    mock_artifact = Mock()
    mock_artifact.type = 1  # ARTIFACT_IMAGE
    mock_artifact.finish_reason = 0  # Success
    mock_artifact.binary = b"fake_image_data"
    
    mock_answer = Mock()
    mock_answer.artifacts = [mock_artifact]
    
    mock_client.generate.return_value = [mock_answer]
    
    return mock_client


class TestSceneManager:
    """Test SceneManager functionality."""
    
    def test_static_scenes_initialization(self):
        """Test that static scenes are initialized correctly."""
        scene_manager = SceneManager()
        scenes = scene_manager.get_all_scenes()
        
        assert len(scenes) == 8
        assert "Scene 1" in scenes
        assert scenes["Scene 1"].name == "The Stochastic Parrot"
    
    def test_generate_scenes(self, mock_api_config, mock_openai_client):
        """Test dynamic scene generation."""
        with patch('content_generator.OpenAI', return_value=mock_openai_client):
            with patch('content_generator.client.StabilityInference'):
                content_gen = ContentGenerator(mock_api_config)
                scene_manager = SceneManager(content_gen)
                
                scenes = scene_manager.generate_scenes("Test Topic", num_scenes=2)
                
                assert len(scenes) == 2
                assert "Scene 1" in scenes
                assert scenes["Scene 1"].name == "Test Scene 1"
                assert scenes["Scene 1"].narration == "This is a test narration for the first scene."


class TestContentGenerator:
    """Test ContentGenerator functionality."""
    
    @patch('content_generator.client.StabilityInference')
    @patch('content_generator.OpenAI')
    def test_initialization(self, mock_openai, mock_stability, mock_api_config):
        """Test ContentGenerator initialization."""
        with patch('os.makedirs'):
            content_gen = ContentGenerator(mock_api_config)
            
            assert content_gen.config == mock_api_config
            mock_openai.assert_called_once()
            mock_stability.assert_called_once()
    
    @patch('content_generator.client.StabilityInference')
    @patch('content_generator.OpenAI')
    def test_generate_structured_output(self, mock_openai, mock_stability, mock_api_config, mock_openai_client):
        """Test structured scene generation from topic."""
        mock_openai.return_value = mock_openai_client
        
        with patch('os.makedirs'):
            content_gen = ContentGenerator(mock_api_config)
            scenes = content_gen.generate_structured_output("Test Topic", 2)
            
            assert len(scenes) == 2
            assert scenes[0]["name"] == "Test Scene 1"
            assert "prompt" in scenes[0]
            assert "narration" in scenes[0]
    
    @patch('content_generator.client.StabilityInference')
    @patch('content_generator.OpenAI')
    @patch('builtins.open', new_callable=mock_open)
    def test_generate_audio(self, mock_file, mock_openai, mock_stability, mock_api_config, mock_openai_client):
        """Test audio generation."""
        mock_openai.return_value = mock_openai_client
        
        with patch('os.makedirs'):
            content_gen = ContentGenerator(mock_api_config)
            audio_path = content_gen.generate_audio("Test narration", "Scene 1")
            
            assert audio_path.endswith(".mp3")
            assert "Scene_1" in audio_path
    
    @patch('content_generator.client.StabilityInference')
    @patch('content_generator.OpenAI')
    @patch('PIL.Image.open')
    @patch('builtins.open', new_callable=mock_open)
    def test_generate_image(self, mock_file, mock_pil, mock_openai, mock_stability, mock_api_config, mock_stability_client):
        """Test image generation."""
        mock_stability.return_value = mock_stability_client
        
        with patch('os.makedirs'):
            content_gen = ContentGenerator(mock_api_config)
            scene = Scene(id="Scene 1", name="Test", prompt="Test prompt")
            
            with patch('os.path.join', return_value="/tmp/test.png"):
                image_path = content_gen.generate_image(scene)
                
                # Verify Stability API was called
                mock_stability_client.generate.assert_called_once()


class TestMediaGenerationPipeline:
    """Test MediaGenerationPipeline orchestration."""
    
    @patch('main.VideoAssembler')
    @patch('main.ImageProcessor')
    @patch('main.ContentGenerator')
    @patch('main.SceneManager')
    def test_pipeline_initialization_static(self, mock_scene_mgr, mock_content_gen, mock_img_proc, mock_video_asm, mock_api_config):
        """Test pipeline initialization with static scenes."""
        with patch('os.makedirs'):
            pipeline = MediaGenerationPipeline(mock_api_config, use_static_scenes=True)
            
            assert pipeline.config == mock_api_config
            assert pipeline.use_static_scenes is True
            mock_scene_mgr.assert_called_once()
            mock_content_gen.assert_called_once()
    
    @patch('main.VideoAssembler')
    @patch('main.ImageProcessor')
    @patch('main.ContentGenerator')
    @patch('main.SceneManager')
    def test_pipeline_initialization_dynamic(self, mock_scene_mgr, mock_content_gen, mock_img_proc, mock_video_asm, mock_api_config):
        """Test pipeline initialization for dynamic scenes."""
        with patch('os.makedirs'):
            pipeline = MediaGenerationPipeline(mock_api_config, use_static_scenes=False)
            
            assert pipeline.use_static_scenes is False
    
    @patch('main.VideoAssembler')
    @patch('main.ImageProcessor')
    @patch('main.ContentGenerator')
    @patch('main.SceneManager')
    def test_generate_content_with_audio(self, mock_scene_mgr, mock_content_gen, mock_img_proc, mock_video_asm, mock_api_config):
        """Test content generation with audio."""
        # Setup mocks
        mock_scene = Scene(
            id="Scene 1",
            name="Test Scene",
            prompt="Test prompt",
            narration="Test narration"
        )
        
        mock_scene_mgr_instance = Mock()
        mock_scene_mgr_instance.get_all_scenes.return_value = {"Scene 1": mock_scene}
        mock_scene_mgr_instance.update_scene_results = Mock()
        mock_scene_mgr.return_value = mock_scene_mgr_instance
        
        mock_content_gen_instance = Mock()
        mock_content_gen_instance.process_all_scenes.return_value = {
            "Scene 1": {"narration": "Test narration", "image_file": "/tmp/test.png"}
        }
        mock_content_gen_instance.generate_audio.return_value = "/tmp/test.mp3"
        mock_content_gen.return_value = mock_content_gen_instance
        
        with patch('os.makedirs'):
            pipeline = MediaGenerationPipeline(mock_api_config)
            results = pipeline.generate_content(generate_audio=True)
            
            # Verify audio generation was called
            mock_content_gen_instance.generate_audio.assert_called_once()
            assert "Scene 1" in results


class TestConfig:
    """Test configuration classes."""
    
    def test_llm_config_defaults(self):
        """Test LLMConfig default values."""
        config = LLMConfig()
        
        assert config.scene_generation_model == "gpt-4o-mini"
        assert "JSON" in config.scene_generation_prompt
    
    def test_tts_config_defaults(self):
        """Test TTSConfig default values."""
        config = TTSConfig()
        
        assert config.tts_model == "tts-1"
        assert config.tts_voice == "alloy"
        assert "audio" in config.audio_output_dir
    
    def test_api_config_post_init(self):
        """Test APIConfig initialization of sub-configs."""
        config = APIConfig(
            openai_api_key="test-key",
            stability_api_key="test-key"
        )
        
        assert config.llm_config is not None
        assert isinstance(config.llm_config, LLMConfig)
        assert config.tts_config is not None
        assert isinstance(config.tts_config, TTSConfig)
