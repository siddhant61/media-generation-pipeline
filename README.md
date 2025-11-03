# Media Generation Pipeline

A comprehensive Python pipeline for generating dynamic video content using AI-powered scene generation, narration, and image generation. This project transforms any topic into a complete video narrative with synchronized audio, automated text overlays, and professional MP4 output.

## 🚀 Features

### Core Pipeline
- **🎬 Dynamic Scene Generation**: LLM-powered scene creation from any topic
- **🎙️ Text-to-Speech Audio**: OpenAI TTS integration for professional narration
- **🎨 AI Image Generation**: Stability AI for stunning visual content
- **🎥 MP4 Video Assembly**: MoviePy-based video creation with audio synchronization

### Production Features (Phase 5)
- **🎬 Ken Burns Effect**: Smooth zoom-and-pan animations on static images
- **🎵 Background Music**: Mix background music with narration at configurable volume
- **📝 Subtitle Burning**: Automatic subtitle generation from narration text
- **🎨 Customizable Styling**: Configure fonts, colors, and positioning

### API & Scalability (Phase 6)
- **🚀 FastAPI Server**: RESTful API with asynchronous job processing
- **📊 Job Tracking**: Real-time status updates for video generation
- **📁 Static File Serving**: Direct access to generated videos via URL
- **🔄 Background Tasks**: Non-blocking video generation with progress tracking

### Additional Features
- **📊 Legacy Support**: Optional GIF animations and storyboards
- **🏗️ Modular Architecture**: Clean, maintainable code structure
- **⚙️ Flexible Configuration**: Topic-based or static scene workflows
- **🔒 Robust Error Handling**: Graceful handling of API errors and rate limits
- **🧪 Tested**: Comprehensive test suite with mocked API calls (25 tests)

## 📁 Project Structure

```
media_generation_pipeline/
├── config.py              # Configuration with LLM, TTS, Video, and API settings
├── scene_manager.py       # Dynamic and static scene management
├── content_generator.py   # OpenAI (LLM, TTS) and Stability AI integration
├── image_processor.py     # Image processing and visualization
├── video_assembler.py     # MP4 video creation with production features
├── cli.py                 # Command-line interface (CLI)
├── main.py                # FastAPI server for REST API
├── setup.py               # Standard setuptools configuration
├── requirements.txt       # Python dependencies
├── tests/                 # Test suite with pytest
│   ├── __init__.py
│   ├── test_pipeline.py   # Pipeline tests (12 tests)
│   └── test_api.py        # API endpoint tests (13 tests)
├── README.md              # This file
├── API.md                 # API documentation
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

# Optional - Model Configuration
LLM_MODEL=gpt-4o-mini          # Scene generation model
TTS_MODEL=tts-1                 # Text-to-speech model
TTS_VOICE=alloy                 # Voice (alloy, echo, fable, onyx, nova, shimmer)
VIDEO_FPS=24                    # Video frame rate
OUTPUT_DIR=generated_content    # Output directory

# Optional - Production Features
BACKGROUND_MUSIC_FILE=/path/to/music.mp3  # Background music for videos
```

### Configuration Classes

The pipeline includes four configuration classes in `config.py`:

- **`LLMConfig`**: Scene generation settings (model, prompts)
- **`TTSConfig`**: Text-to-speech settings (model, voice, output directory)
- **`VideoConfig`**: Production features (Ken Burns effect, background music, subtitles)
- **`APIConfig`**: Main configuration (API keys, Stability AI settings, output settings)

## 🎬 Usage Modes

### CLI Mode - Direct Command Line

Use the CLI for quick video generation:

```bash
# Generate video from topic
python cli.py "The History of Space Exploration"

# Or using the installed command
media-pipeline "Climate Change" --num-scenes 6
```

### API Mode - REST Server

Run the FastAPI server for programmatic access:

```bash
# Start the API server
uvicorn main:app --host 0.0.0.0 --port 8000

# Or using the installed command
media-pipeline-api
```

Then use the REST API:
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "The Solar System", "num_scenes": 8}'
```

See [API.md](API.md) for full API documentation.

## 🎬 Two Operating Modes

### 1. Dynamic Mode (Default) - Topic-Based Generation

Simply provide a topic, and the pipeline will:
1. Generate 8 scenes using LLM (customizable count)
2. Create narration for each scene
3. Generate images based on scene descriptions
4. Synthesize audio narration
5. Apply production features (Ken Burns, music, subtitles)
6. Assemble everything into an MP4 video

**CLI:**
```bash
python cli.py "The History of Space Exploration"
```

**API:**
```bash
curl -X POST http://localhost:8000/generate \
  -d '{"topic": "Space Exploration", "num_scenes": 8}'
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

**CLI:**
```bash
python cli.py --static-scenes
```

**API:**
```bash
curl -X POST http://localhost:8000/generate \
  -d '{"use_static_scenes": true}'
```

## 🎯 Usage

### CLI Usage

#### Basic Usage - Dynamic Topic-Based Video Generation

Generate a complete video from any topic:

```bash
# Generate 8 scenes (default)
python cli.py "The Industrial Revolution"

# Generate custom number of scenes
python cli.py "Climate Change" --num-scenes 5

# Using the installed console script
media-pipeline "Ancient Egypt"
```

#### Advanced CLI Usage

**Static scenes mode**:
```bash
# Use predefined scenes
python cli.py --static-scenes

# Process specific predefined scenes
python cli.py --static-scenes --scenes "Scene 1" "Scene 2" "Scene 3"

# Process a single predefined scene
python cli.py --static-scenes --single "Scene 1"
```

**Content generation options**:
```bash
# Generate content only (no video assembly)
python cli.py "Space Exploration" --content-only

# Custom output directory
python cli.py "Quantum Physics" --output-dir /path/to/custom/output
```

### API Server Usage

Start the FastAPI server and use REST endpoints for video generation:

```bash
# Start the server
uvicorn main:app --host 0.0.0.0 --port 8000

# Submit a job
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "The Renaissance", "num_scenes": 6}'

# Check job status
curl http://localhost:8000/status/{job_id}

# List all jobs
curl http://localhost:8000/jobs

# Access generated video
curl http://localhost:8000/outputs/final_video.mp4
```

For complete API documentation with Python, JavaScript, and cURL examples, see **[API.md](API.md)**.

**Testing**:
```bash
# Run all tests (CLI + API)
pytest tests/ -v

# Run specific test suite
pytest tests/test_pipeline.py -v  # Pipeline tests
pytest tests/test_api.py -v       # API tests

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Python SDK Usage

```python
from cli import MediaGenerationPipeline
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

### Customizing Production Features

Enable/disable and configure production features:

```python
from config import config

# Ken Burns Effect
config.video_config.ken_burns_enabled = True
config.video_config.ken_burns_zoom_ratio = 1.15  # 15% zoom

# Background Music
config.video_config.background_music_file = "/path/to/music.mp3"
config.video_config.background_music_volume = 0.15  # 15% volume

# Subtitles
config.video_config.subtitles_enabled = True
config.video_config.subtitle_fontsize = 28
config.video_config.subtitle_color = "yellow"
config.video_config.subtitle_position = "bottom"  # or "top", "center"
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

## ✅ Recent Updates

### v2.1.0 - Production Features & API Layer (Current)

**Phase 5 - Production Features:**
- ✅ **Ken Burns Effect**: Smooth zoom-and-pan animations on images
- ✅ **Background Music**: Mix background music with narration
- ✅ **Subtitle Burning**: Automatic subtitle generation with customizable styling
- ✅ **MoviePy 2.x Compatibility**: Updated imports for latest version

**Phase 6 - API & Scalability:**
- ✅ **FastAPI Server**: RESTful API with async job processing
- ✅ **Job Tracking**: Real-time status updates (7 job states)
- ✅ **Static File Serving**: Direct video access via URL
- ✅ **API Tests**: 13 comprehensive tests for all endpoints
- ✅ **API Documentation**: Complete guide with Python, JS, and cURL examples
- ✅ **Dual Console Scripts**: `media-pipeline` (CLI) and `media-pipeline-api` (server)

### v2.0.0 - Core Pipeline

- ✅ **Dynamic Scene Generation**: LLM-powered scene creation from any topic
- ✅ **Text-to-Speech Integration**: OpenAI TTS for professional narration
- ✅ **MP4 Video Output**: MoviePy-based video assembly with audio sync
- ✅ **Robust Error Handling**: Graceful handling of API rate limits and errors
- ✅ **Test Suite**: Comprehensive pytest-based tests with mocked APIs
- ✅ **Standard Setup**: setuptools-based installation with console scripts

## 🔮 Future Enhancements

- [ ] Redis-based job storage for persistence
- [ ] Web UI for video management and preview
- [ ] Support for additional AI models (Anthropic Claude, Google Gemini)
- [ ] Batch processing capabilities for multiple topics
- [ ] More advanced video effects and transitions
- [ ] Support for multiple languages and voices
- [ ] Cloud storage integration (S3, GCS, Azure Blob)
- [ ] Webhook notifications for job completion 