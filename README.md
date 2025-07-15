# Media Generation Pipeline

A comprehensive Python pipeline for generating video content using AI-powered narration and image generation. This project transforms scene descriptions into complete visual narratives with automated text overlays, transitions, and storyboards.

## 🚀 Features

- **AI-Powered Content Generation**: Uses OpenAI for narration and Stability AI for image generation
- **Scene Management**: Organized scene-based workflow with detailed prompts
- **Image Processing**: Automated text overlays, transitions, and storyboard creation
- **Animation Support**: Generates animated GIFs with smooth transitions
- **Modular Architecture**: Clean, maintainable code structure with separate modules
- **Command-Line Interface**: Easy-to-use CLI for running the pipeline

## 📁 Project Structure

```
media_generation_pipeline/
├── config.py              # Configuration and API settings
├── scene_manager.py       # Scene definitions and management
├── content_generator.py   # OpenAI and Stability AI integration
├── image_processor.py     # Image processing and visualization
├── main.py                # Main pipeline orchestrator
├── requirements.txt       # Python dependencies
├── README.md              # This file
└── generated_content/     # Output directory (created automatically)
    ├── transitions/       # Transition frames
    ├── overlays/          # Text overlay images
    └── storyboards/       # Generated storyboards
```

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd media_generation_pipeline
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up API keys**:
   ```bash
   export OPENAI_API_KEY='your-openai-api-key'
   export STABILITY_API_KEY='your-stability-api-key'
   ```

## 🔧 Configuration

The pipeline uses environment variables for API keys. You can also modify settings in `config.py`:

```python
# API Settings
openai_model = "gpt-4o-mini"
stability_width = 512
stability_height = 512

# Output Settings
output_dir = "generated_content"
font_size = 40
```

## 📝 Scene Definitions

The pipeline includes 8 predefined scenes for educational content about AI:

1. **The Stochastic Parrot** - Abstract digital artwork with AI themes
2. **Life as a Complex Stochastic Parrot** - Transition to organic structures
3. **Evolution and Functional Information** - Darwin-inspired visualization
4. **The AI Pipeline** - Technical diagram of AI processes
5. **The Alchemist Tribe (Anime Style)** - Anime-style AI workshop
6. **The Alchemist Tribe's Story** - Anime storyboard sequence
7. **Teaser and Perspective Shift** - Cinematic transition
8. **The Supervisor's Question** - Close-up portrait with dialogue

## 🎯 Usage

### Basic Usage

Run the complete pipeline for all scenes:
```bash
python main.py
```

### Advanced Usage

**Process specific scenes**:
```bash
python main.py --scenes "Scene 1" "Scene 2" "Scene 3"
```

**Process a single scene**:
```bash
python main.py --single "Scene 1"
```

**Generate content only (no visualizations)**:
```bash
python main.py --content-only
```

**Create visualizations only**:
```bash
python main.py --visualizations-only
```

**Custom output directory**:
```bash
python main.py --output-dir /path/to/custom/output
```

### Python API Usage

```python
from main import MediaGenerationPipeline
from config import config

# Initialize pipeline
pipeline = MediaGenerationPipeline(config)

# Run complete pipeline
results = pipeline.run_complete_pipeline()

# Process single scene
single_result = pipeline.generate_single_scene("Scene 1")

# Generate content only
content_results = pipeline.generate_content(["Scene 1", "Scene 2"])
```

## 📊 Output Files

The pipeline generates several types of output:

### Content Generation
- **Images**: PNG files for each scene (`Scene_1.png`, `Scene_2.png`, etc.)
- **Narration**: Text content stored in scene objects

### Visualizations
- **Text Overlays**: Images with scene titles (`text_Scene_1.png`)
- **Storyboard**: Combined grid view of all scenes (`complete_storyboard.png`)
- **Animation**: Animated GIF with transitions (`complete_animation.gif`)
- **Transitions**: Individual transition frames between scenes

## 🔄 Pipeline Workflow

1. **Scene Initialization**: Load predefined scenes with prompts
2. **Content Generation**:
   - Generate narration using OpenAI
   - Generate images using Stability AI
3. **Image Processing**:
   - Create text overlays
   - Generate transition frames
4. **Visualization Creation**:
   - Compile storyboard
   - Create animated GIF

## 🎨 Customization

### Adding New Scenes

Edit `scene_manager.py` to add new scenes:

```python
"Scene 9": {
    "name": "Your Scene Name",
    "prompt": "Detailed description for image generation..."
}
```

### Modifying Image Processing

Customize image processing in `image_processor.py`:

```python
# Change text overlay position
overlay_path = self.image_processor.add_text_overlay(
    image_path, 
    text,
    position='top',  # 'top', 'center', 'bottom'
    font_size=50
)

# Adjust transition frames
transition_frames = self.generate_transition(
    scene1_img, 
    scene2_img, 
    num_frames=10  # More frames for smoother transitions
)
```

### API Configuration

Modify API settings in `config.py`:

```python
# OpenAI Settings
openai_model = "gpt-4"  # Use different model
temperature = 0.8       # More creative output

# Stability AI Settings
stability_width = 1024  # Higher resolution
stability_height = 1024
stability_steps = 100   # More generation steps
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

## 🔮 Future Enhancements

- [ ] Video generation with audio narration
- [ ] Support for additional AI models
- [ ] Web interface for scene management
- [ ] Batch processing capabilities
- [ ] Integration with video editing software
- [ ] Real-time preview functionality 