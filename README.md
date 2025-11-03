# Media Generation Pipeline

A comprehensive Python pipeline for generating dynamic video content using AI-powered scene generation, narration, and image generation. This project transforms any topic into a complete video narrative with synchronized audio, automated text overlays, and professional MP4 output.

## 🚀 Features

- **🎬 Dynamic Scene Generation**: LLM-powered scene creation from any topic
- **🎙️ Text-to-Speech Audio**: OpenAI TTS integration for professional narration
- **🎨 AI Image Generation**: Stability AI for stunning visual content
- **🎥 MP4 Video Assembly**: MoviePy-based video creation with audio synchronization
- **📊 Legacy Support**: Optional GIF animations and storyboards
- **🏗️ Modular Architecture**: Clean, maintainable code structure
- **⚙️ Flexible Configuration**: Topic-based or static scene workflows
- **🔒 Robust Error Handling**: Graceful handling of API errors and rate limits
- **🧪 Tested**: Comprehensive test suite with mocked API calls

## 📁 Project Structure

```
media_generation_pipeline/
├── config.py              # Configuration with LLM, TTS, and API settings
├── scene_manager.py       # Dynamic and static scene management
├── content_generator.py   # OpenAI (LLM, TTS) and Stability AI integration
├── image_processor.py     # Image processing and visualization
├── video_assembler.py     # MP4 video creation with audio sync
├── main.py                # Main pipeline orchestrator with CLI
├── setup.py               # Standard setuptools configuration
├── requirements.txt       # Python dependencies
├── tests/                 # Test suite with pytest
│   ├── __init__.py
│   └── test_pipeline.py
├── README.md              # This file
└── generated_content/     # Output directory (created automatically)
    ├── audio/             # Generated audio files (MP3)
    ├── transitions/       # Transition frames
    ├── overlays/          # Text overlay images
    └── storyboards/       # Generated storyboards
```

## 🛠️ Installation

### Option 1: Using pip (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/siddhant61/media-generation-pipeline.git
   cd media-generation-pipeline
   ```

2. **Install the package**:
   ```bash
   pip install -e .
   ```

3. **Set up API keys**:
   ```bash
   export OPENAI_API_KEY='your-openai-api-key'
   export STABILITY_API_KEY='your-stability-api-key'
   ```

### Option 2: Using requirements.txt

1. **Clone and navigate**:
   ```bash
   git clone https://github.com/siddhant61/media-generation-pipeline.git
   cd media-generation-pipeline
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API keys** (same as above)

## 🔧 Configuration

The pipeline uses environment variables for API keys and offers extensive configuration options:

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Required
OPENAI_API_KEY=your-openai-api-key
STABILITY_API_KEY=your-stability-api-key

# Optional
LLM_MODEL=gpt-4o-mini          # Scene generation model
TTS_MODEL=tts-1                 # Text-to-speech model
TTS_VOICE=alloy                 # Voice (alloy, echo, fable, onyx, nova, shimmer)
VIDEO_FPS=24                    # Video frame rate
OUTPUT_DIR=generated_content    # Output directory
```

### Configuration Classes

The pipeline includes three configuration classes in `config.py`:

- **`LLMConfig`**: Scene generation settings (model, prompts)
- **`TTSConfig`**: Text-to-speech settings (model, voice, output directory)
- **`APIConfig`**: Main configuration (API keys, Stability AI settings, output settings)

## 🎬 Two Operating Modes

### 1. Dynamic Mode (Default) - Topic-Based Generation

Simply provide a topic, and the pipeline will:
1. Generate 8 scenes using LLM (customizable count)
2. Create narration for each scene
3. Generate images based on scene descriptions
4. Synthesize audio narration
5. Assemble everything into an MP4 video

```bash
python main.py "The History of Space Exploration"
```

### 2. Static Mode - Predefined Scenes

Use the 8 predefined scenes for educational content about AI:

1. **The Stochastic Parrot** - Abstract digital artwork with AI themes
2. **Life as a Complex Stochastic Parrot** - Transition to organic structures
3. **Evolution and Functional Information** - Darwin-inspired visualization
4. **The AI Pipeline** - Technical diagram of AI processes
5. **The Alchemist Tribe (Anime Style)** - Anime-style AI workshop
6. **The Alchemist Tribe's Story** - Anime storyboard sequence
7. **Teaser and Perspective Shift** - Cinematic transition
8. **The Supervisor's Question** - Close-up portrait with dialogue

```bash
python main.py --static-scenes
```

## 🎯 Usage

### Basic Usage - Dynamic Topic-Based Video Generation

Generate a complete video from any topic:

```bash
# Generate 8 scenes (default)
python main.py "The Industrial Revolution"

# Generate custom number of scenes
python main.py "Climate Change" --num-scenes 5

# Using the installed console script
media-pipeline "Ancient Egypt"
```

### Advanced Usage

**Static scenes mode**:
```bash
# Use predefined scenes
python main.py --static-scenes

# Process specific predefined scenes
python main.py --static-scenes --scenes "Scene 1" "Scene 2" "Scene 3"

# Process a single predefined scene
python main.py --static-scenes --single "Scene 1"
```

**Content generation options**:
```bash
# Generate content only (no video assembly)
python main.py "Space Exploration" --content-only

# Custom output directory
python main.py "Quantum Physics" --output-dir /path/to/custom/output
```

**Testing without API calls**:
```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Python API Usage

```python
from main import MediaGenerationPipeline
from config import config

# Dynamic mode - generate video from topic
pipeline = MediaGenerationPipeline(config, use_static_scenes=False)
results = pipeline.run_complete_pipeline(
    topic="The Renaissance",
    num_scenes=6
)

# Static mode - use predefined scenes
pipeline_static = MediaGenerationPipeline(config, use_static_scenes=True)
results = pipeline_static.run_complete_pipeline()

# Process specific scenes only
content_results = pipeline.generate_content(["Scene 1", "Scene 2"])

# Generate single scene (static mode only)
single_result = pipeline_static.generate_single_scene("Scene 1")
```

## 📊 Output Files

The pipeline generates several types of output in the `generated_content/` directory:

### Primary Output
- **🎥 Video**: `final_video.mp4` - Complete video with synchronized audio and text overlays

### Content Generation
- **🖼️ Images**: PNG files for each scene (`Scene_1.png`, `Scene_2.png`, etc.)
- **🎙️ Audio**: MP3 narration files in `audio/` subdirectory (`Scene_1.mp3`, etc.)
- **📝 Narration**: Text content stored in scene objects and embedded in video

### Optional Visualizations
- **🖼️ Text Overlays**: Images with scene titles in `overlays/` subdirectory
- **📋 Storyboard**: Combined grid view of all scenes (`complete_storyboard.png`)
- **🎞️ GIF Animation**: Legacy animated GIF with transitions (`complete_animation.gif`)
- **🔄 Transitions**: Individual transition frames in `transitions/` subdirectory

## 🔄 Pipeline Workflow

### Dynamic Mode (Topic-Based)
1. **Scene Generation**: LLM generates scenes from topic (name, prompt, narration)
2. **Content Generation**:
   - Generate images using Stability AI based on scene prompts
   - Generate audio narration using OpenAI TTS
3. **Image Processing**:
   - Create text overlays with scene titles
   - Prepare frames for video assembly
4. **Video Assembly**:
   - Synchronize images with audio (duration from audio)
   - Concatenate all scenes into final MP4
   - Add transitions and effects

### Static Mode (Predefined Scenes)
1. **Scene Initialization**: Load 8 predefined scenes with detailed prompts
2. **Content Generation**: Same as dynamic mode
3. **Image Processing**: Same as dynamic mode
4. **Video Assembly**: Same as dynamic mode

### Optional Outputs
- Storyboard compilation
- Legacy GIF animation with transitions

## 🎨 Customization

### Customizing Scene Generation

Modify the LLM prompt for scene generation in `config.py`:

```python
config.llm_config.scene_generation_prompt = """Your custom prompt here..."""
config.llm_config.scene_generation_model = "gpt-4"  # Use GPT-4 for better quality
```

### Customizing Text-to-Speech

Change TTS settings:

```python
from config import config

config.tts_config.tts_model = "tts-1-hd"  # Higher quality TTS
config.tts_config.tts_voice = "nova"      # Different voice
```

### Customizing Video Output

Adjust video assembly settings in `video_assembler.py` or when calling:

```python
video_path = video_assembler.create_video_from_scenes(
    scenes,
    output_filename="my_video.mp4",
    fps=30,  # Higher frame rate
    default_duration=10.0  # Longer default duration
)
```

### Modifying Image Generation

Customize Stability AI settings in `config.py`:

```python
# Higher resolution images
config.stability_width = 1024
config.stability_height = 1024
config.stability_steps = 100  # More steps for better quality
config.stability_cfg_scale = 8.0  # Stronger prompt adherence
```

### Adding Static Scenes

Edit `scene_manager.py` to add new predefined scenes:

```python
"Scene 9": {
    "name": "Your Scene Name",
    "prompt": "Detailed description for image generation..."
}
```

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**:
   - Ensure environment variables are set correctly
   - Check API key validity and quotas

2. **Font Issues**:
   - On Linux: Install `fonts-dejavu` package
   - On macOS: System fonts should work automatically
   - On Windows: Arial font is usually available

3. **Memory Issues**:
   - Reduce image dimensions in config
   - Process scenes individually using `--single`

4. **Generation Failures**:
   - Check internet connection
   - Verify API key permissions
   - Review prompt content for policy compliance

### Debug Mode

Enable verbose output by modifying the Stability AI client:

```python
self.stability_api = client.StabilityInference(
    key=self.config.stability_api_key,
    verbose=True  # Enable debug output
)
```

## 📄 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Check the troubleshooting section above
- Review the code documentation
- Open an issue on GitHub

## ✅ Recent Updates (v2.0.0)

- ✅ **Dynamic Scene Generation**: LLM-powered scene creation from any topic
- ✅ **Text-to-Speech Integration**: OpenAI TTS for professional narration
- ✅ **MP4 Video Output**: MoviePy-based video assembly with audio sync
- ✅ **Robust Error Handling**: Graceful handling of API rate limits and errors
- ✅ **Test Suite**: Comprehensive pytest-based tests with mocked APIs
- ✅ **Standard Setup**: setuptools-based installation with console scripts

## 🔮 Future Enhancements

- [ ] Support for additional AI models (Anthropic Claude, Google Gemini)
- [ ] Web interface for scene management and preview
- [ ] Batch processing capabilities for multiple topics
- [ ] Advanced video effects and transitions
- [ ] Support for multiple languages and voices
- [ ] Real-time preview functionality
- [ ] Cloud deployment options (AWS, GCP, Azure) 