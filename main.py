#!/usr/bin/env python3
"""
Main pipeline script for the Media Generation Pipeline.
Orchestrates the entire video generation process from scene definition to final output.
"""

import os
import sys
import argparse
from typing import List, Dict, Any

from config import config
from scene_manager import SceneManager
from content_generator import ContentGenerator
from image_processor import ImageProcessor

class MediaGenerationPipeline:
    """Main pipeline class that orchestrates the entire video generation process."""
    
    def __init__(self, api_config=None):
        """Initialize the pipeline with all components."""
        self.config = api_config or config
        
        # Initialize components
        self.scene_manager = SceneManager()
        self.content_generator = ContentGenerator(self.config)
        self.image_processor = ImageProcessor(self.config)
        
        print("Media Generation Pipeline initialized successfully!")
        print(f"Output directory: {self.config.output_dir}")
        print(self.scene_manager.get_scene_summary())
    
    def generate_content(self, scene_ids: List[str] = None) -> Dict[str, Any]:
        """
        Generate narration and images for specified scenes.
        
        Args:
            scene_ids: List of scene IDs to process. If None, processes all scenes.
            
        Returns:
            Dictionary containing results for all processed scenes
        """
        scenes = self.scene_manager.get_all_scenes()
        
        # Filter scenes if specific IDs are provided
        if scene_ids:
            scenes = {sid: scene for sid, scene in scenes.items() if sid in scene_ids}
        
        print(f"\n=== CONTENT GENERATION ===")
        print(f"Processing {len(scenes)} scenes...")
        
        # Generate content for all scenes
        results = self.content_generator.process_all_scenes(scenes)
        
        return results
    
    def create_visualizations(self, results: Dict[str, Any]) -> Dict[str, str]:
        """
        Create visualizations including storyboards and animations.
        
        Args:
            results: Results from content generation
            
        Returns:
            Dictionary containing paths to created visualizations
        """
        print(f"\n=== VISUALIZATION CREATION ===")
        
        # Get all scene images and create text overlays
        scene_images = []
        annotated_images = []
        captions = []
        
        scenes = self.scene_manager.get_all_scenes()
        
        for scene_id, scene in scenes.items():
            if scene.image_file and os.path.exists(scene.image_file):
                scene_images.append(scene.image_file)
                
                # Add text overlay
                overlay_path = self.image_processor.add_text_overlay(
                    scene.image_file, 
                    scene.name,
                    position='bottom'
                )
                annotated_images.append(overlay_path)
                
                # Create caption for storyboard
                caption = f"{scene_id}: {scene.name}\n{scene.narration[:100]}..."
                captions.append(caption)
        
        visualization_paths = {}
        
        # Create storyboard
        if annotated_images:
            storyboard_path = self.image_processor.create_storyboard(
                annotated_images, 
                captions,
                "complete_storyboard.png"
            )
            visualization_paths['storyboard'] = storyboard_path
        
        # Create animated GIF
        if scene_images:
            animation_path = self.image_processor.create_animated_gif(
                scene_images,
                "complete_animation.gif",
                duration=2000,  # 2 seconds per frame
                include_transitions=True
            )
            visualization_paths['animation'] = animation_path
        
        return visualization_paths
    
    def run_complete_pipeline(self, scene_ids: List[str] = None) -> Dict[str, Any]:
        """
        Run the complete pipeline: generate content and create visualizations.
        
        Args:
            scene_ids: List of scene IDs to process. If None, processes all scenes.
            
        Returns:
            Dictionary containing all results and output paths
        """
        print("Starting complete media generation pipeline...")
        
        # Step 1: Generate content
        content_results = self.generate_content(scene_ids)
        
        # Step 2: Create visualizations
        visualization_results = self.create_visualizations(content_results)
        
        # Combine results
        pipeline_results = {
            'content': content_results,
            'visualizations': visualization_results,
            'output_directory': self.config.output_dir
        }
        
        # Print summary
        print(f"\n=== PIPELINE COMPLETE ===")
        print(f"Content generated for {len(content_results)} scenes")
        print(f"Output directory: {self.config.output_dir}")
        
        if visualization_results.get('storyboard'):
            print(f"Storyboard created: {visualization_results['storyboard']}")
        
        if visualization_results.get('animation'):
            print(f"Animation created: {visualization_results['animation']}")
        
        return pipeline_results
    
    def generate_single_scene(self, scene_id: str) -> Dict[str, Any]:
        """
        Generate content for a single scene.
        
        Args:
            scene_id: ID of the scene to process
            
        Returns:
            Dictionary containing scene results
        """
        scene = self.scene_manager.get_scene(scene_id)
        if not scene:
            print(f"Scene {scene_id} not found")
            return {}
        
        print(f"Processing single scene: {scene_id}")
        result = self.content_generator.generate_scene_content(scene)
        
        # Update scene manager
        self.scene_manager.update_scene_results(
            scene_id, 
            result['narration'], 
            result['image_file']
        )
        
        return {scene_id: result}


def main():
    """Main entry point for the pipeline."""
    parser = argparse.ArgumentParser(description='Media Generation Pipeline')
    parser.add_argument('--scenes', nargs='*', help='Specific scene IDs to process')
    parser.add_argument('--single', type=str, help='Process a single scene')
    parser.add_argument('--content-only', action='store_true', help='Generate content only (no visualizations)')
    parser.add_argument('--visualizations-only', action='store_true', help='Create visualizations only (requires existing content)')
    parser.add_argument('--output-dir', type=str, help='Custom output directory')
    
    args = parser.parse_args()
    
    # Validate API keys
    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("Please set the required environment variables:")
        print("  export OPENAI_API_KEY='your-openai-key'")
        print("  export STABILITY_API_KEY='your-stability-key'")
        return 1
    
    # Set custom output directory if provided
    if args.output_dir:
        config.output_dir = args.output_dir
    
    # Initialize pipeline
    try:
        pipeline = MediaGenerationPipeline(config)
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        return 1
    
    # Run pipeline based on arguments
    try:
        if args.single:
            # Process single scene
            results = pipeline.generate_single_scene(args.single)
        elif args.content_only:
            # Generate content only
            results = pipeline.generate_content(args.scenes)
        elif args.visualizations_only:
            # Create visualizations only
            dummy_results = {}  # This would need existing content
            results = pipeline.create_visualizations(dummy_results)
        else:
            # Run complete pipeline
            results = pipeline.run_complete_pipeline(args.scenes)
        
        print("\nPipeline completed successfully!")
        return 0
        
    except Exception as e:
        print(f"Error running pipeline: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 