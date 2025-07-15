#!/usr/bin/env python3
"""
Example usage script for the Media Generation Pipeline.
Demonstrates various ways to use the pipeline components.
"""

import os
from main import MediaGenerationPipeline
from config import config, APIConfig
from scene_manager import SceneManager

def example_complete_pipeline():
    """Example: Run the complete pipeline for all scenes."""
    print("=== Example: Complete Pipeline ===")
    
    # Initialize pipeline
    pipeline = MediaGenerationPipeline()
    
    # Run complete pipeline
    results = pipeline.run_complete_pipeline()
    
    print(f"Pipeline completed! Check output in: {results['output_directory']}")
    return results

def example_single_scene():
    """Example: Process a single scene."""
    print("\n=== Example: Single Scene Processing ===")
    
    pipeline = MediaGenerationPipeline()
    
    # Process just one scene
    result = pipeline.generate_single_scene("Scene 1")
    
    print(f"Single scene processed: {result}")
    return result

def example_specific_scenes():
    """Example: Process specific scenes only."""
    print("\n=== Example: Specific Scenes ===")
    
    pipeline = MediaGenerationPipeline()
    
    # Process only scenes 1, 2, and 3
    specific_scenes = ["Scene 1", "Scene 2", "Scene 3"]
    results = pipeline.run_complete_pipeline(specific_scenes)
    
    print(f"Processed {len(results['content'])} scenes")
    return results

def example_content_only():
    """Example: Generate content without visualizations."""
    print("\n=== Example: Content Only ===")
    
    pipeline = MediaGenerationPipeline()
    
    # Generate content only
    content_results = pipeline.generate_content(["Scene 1", "Scene 2"])
    
    for scene_id, data in content_results.items():
        print(f"{scene_id}: {data['narration'][:100]}...")
    
    return content_results

def example_custom_config():
    """Example: Use custom configuration."""
    print("\n=== Example: Custom Configuration ===")
    
    # Create custom configuration
    custom_config = APIConfig(
        openai_model="gpt-4o-mini",
        temperature=0.8,
        stability_width=1024,
        stability_height=1024,
        output_dir="custom_output"
    )
    
    # Initialize pipeline with custom config
    pipeline = MediaGenerationPipeline(custom_config)
    
    # Process a single scene with custom settings
    result = pipeline.generate_single_scene("Scene 1")
    
    print(f"Custom config result: {result}")
    return result

def example_scene_exploration():
    """Example: Explore available scenes."""
    print("\n=== Example: Scene Exploration ===")
    
    # Initialize scene manager
    scene_manager = SceneManager()
    
    # Print scene summary
    print(scene_manager.get_scene_summary())
    
    # Get specific scene details
    scene = scene_manager.get_scene("Scene 1")
    if scene:
        print(f"\nScene Details:")
        print(f"  ID: {scene.id}")
        print(f"  Name: {scene.name}")
        print(f"  Prompt: {scene.prompt[:200]}...")
    
    return scene_manager

def example_image_processing():
    """Example: Demonstrate image processing features."""
    print("\n=== Example: Image Processing ===")
    
    from image_processor import ImageProcessor
    
    # Initialize image processor
    processor = ImageProcessor()
    
    # This example assumes you have generated some images first
    # You would typically use this after running content generation
    
    print("Image processor initialized with directories:")
    print(f"  Transitions: {processor.transitions_dir}")
    print(f"  Overlays: {processor.overlays_dir}")
    print(f"  Storyboards: {processor.storyboards_dir}")
    
    return processor

def main():
    """Run all examples."""
    print("Media Generation Pipeline - Example Usage")
    print("========================================")
    
    # Check if API keys are set
    try:
        config.validate()
        print("✓ API keys are configured")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        print("\nPlease set your API keys:")
        print("  export OPENAI_API_KEY='your-openai-key'")
        print("  export STABILITY_API_KEY='your-stability-key'")
        return
    
    # Run examples
    try:
        # Start with scene exploration
        example_scene_exploration()
        
        # Uncomment the examples you want to run:
        
        # example_single_scene()
        # example_content_only()
        # example_specific_scenes()
        # example_custom_config()
        # example_complete_pipeline()
        
        print("\n✓ Examples completed successfully!")
        print("\nTo run more examples, uncomment the desired functions in main()")
        
    except Exception as e:
        print(f"✗ Error running examples: {e}")

if __name__ == "__main__":
    main() 