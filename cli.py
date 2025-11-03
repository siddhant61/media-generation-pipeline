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
from video_assembler import VideoAssembler

class MediaGenerationPipeline:
    """Main pipeline class that orchestrates the entire video generation process."""
    
    def __init__(self, api_config=None, use_static_scenes=False):
        """Initialize the pipeline with all components."""
        self.config = api_config or config
        self.use_static_scenes = use_static_scenes
        
        # Initialize components
        self.content_generator = ContentGenerator(self.config)
        self.scene_manager = SceneManager(self.content_generator)
        self.image_processor = ImageProcessor(self.config)
        self.video_assembler = VideoAssembler(self.config)
        
        print("Media Generation Pipeline initialized successfully!")
        print(f"Output directory: {self.config.output_dir}")
        if use_static_scenes:
            print(self.scene_manager.get_scene_summary())
    
    def generate_content(self, scene_ids: List[str] = None, generate_audio: bool = True) -> Dict[str, Any]:
        """
        Generate narration, images, and audio for specified scenes.
        
        Args:
            scene_ids: List of scene IDs to process. If None, processes all scenes.
            generate_audio: Whether to generate audio narration
            
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
        
        # Generate audio for each scene if requested
        if generate_audio:
            print(f"\n=== AUDIO GENERATION ===")
            for scene_id, scene in scenes.items():
                if scene.narration:
                    audio_file = self.content_generator.generate_audio(scene.narration, scene_id)
                    scene.audio_file = audio_file
                    results[scene_id]['audio_file'] = audio_file
                    self.scene_manager.update_scene_results(scene_id, audio_file=audio_file)
        
        return results
    
    def create_visualizations(self, results: Dict[str, Any], create_video: bool = True, create_gif: bool = False) -> Dict[str, str]:
        """
        Create visualizations including video, storyboards, and optional GIF animations.
        
        Args:
            results: Results from content generation
            create_video: Whether to create MP4 video (default: True)
            create_gif: Whether to create GIF animation (default: False, legacy feature)
            
        Returns:
            Dictionary containing paths to created visualizations
        """
        print(f"\n=== VISUALIZATION CREATION ===")
        
        # Get all scene images and create text overlays
        scene_images = []
        annotated_images = []
        captions = []
        
        scenes = self.scene_manager.get_all_scenes()
        scene_list = list(scenes.values())
        
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
        
        # Create video with audio (primary output)
        if create_video and scene_list:
            video_path = self.video_assembler.create_video_with_text_overlays(
                scene_list,
                self.image_processor,
                "final_video.mp4",
                fps=24
            )
            visualization_paths['video'] = video_path
        
        # Create storyboard
        if annotated_images:
            storyboard_path = self.image_processor.create_storyboard(
                annotated_images, 
                captions,
                "complete_storyboard.png"
            )
            visualization_paths['storyboard'] = storyboard_path
        
        # Create animated GIF (optional, legacy feature)
        if create_gif and scene_images:
            animation_path = self.image_processor.create_animated_gif(
                scene_images,
                "complete_animation.gif",
                duration=2000,  # 2 seconds per frame
                include_transitions=True
            )
            visualization_paths['animation'] = animation_path
        
        return visualization_paths
    
    def run_complete_pipeline(self, topic: str = None, scene_ids: List[str] = None, num_scenes: int = 8) -> Dict[str, Any]:
        """
        Run the complete pipeline: generate content and create visualizations.
        
        Args:
            topic: Topic to generate scenes about (for dynamic generation)
            scene_ids: List of scene IDs to process (for static scenes). If None, processes all scenes.
            num_scenes: Number of scenes to generate (only used with topic)
            
        Returns:
            Dictionary containing all results and output paths
        """
        print("Starting complete media generation pipeline...")
        
        # Step 0: Generate scenes dynamically if topic is provided
        if topic and not self.use_static_scenes:
            print(f"\n=== DYNAMIC SCENE GENERATION ===")
            print(f"Generating scenes for topic: {topic}")
            self.scene_manager.generate_scenes(topic, num_scenes)
            print("Dynamic scene generation complete!")
        
        # Step 1: Generate content
        content_results = self.generate_content(scene_ids)
        
        # Step 2: Create visualizations
        visualization_results = self.create_visualizations(content_results)
        
        # Combine results
        pipeline_results = {
            'content': content_results,
            'visualizations': visualization_results,
            'output_directory': self.config.output_dir,
            'topic': topic
        }
        
        # Print summary
        print(f"\n=== PIPELINE COMPLETE ===")
        print(f"Content generated for {len(content_results)} scenes")
        print(f"Output directory: {self.config.output_dir}")
        
        if visualization_results.get('video'):
            print(f"✅ Video created: {visualization_results['video']}")
        
        if visualization_results.get('storyboard'):
            print(f"Storyboard created: {visualization_results['storyboard']}")
        
        if visualization_results.get('animation'):
            print(f"GIF animation created: {visualization_results['animation']}")
        
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
    parser = argparse.ArgumentParser(description='Media Generation Pipeline - Dynamic Video Generator')
    parser.add_argument('topic', nargs='?', help='Topic to generate video about (e.g., "The Industrial Revolution")')
    parser.add_argument('--num-scenes', type=int, default=8, help='Number of scenes to generate (default: 8)')
    parser.add_argument('--static-scenes', action='store_true', help='Use predefined static scenes instead of generating from topic')
    parser.add_argument('--scenes', nargs='*', help='Specific scene IDs to process (only with --static-scenes)')
    parser.add_argument('--single', type=str, help='Process a single scene (only with --static-scenes)')
    parser.add_argument('--content-only', action='store_true', help='Generate content only (no visualizations)')
    parser.add_argument('--visualizations-only', action='store_true', help='Create visualizations only (requires existing content)')
    parser.add_argument('--output-dir', type=str, help='Custom output directory')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.static_scenes and not args.topic and not args.visualizations_only:
        parser.error("Please provide a topic, or use --static-scenes to use predefined scenes")
    
    if args.static_scenes and not args.topic and not args.scenes and not args.single and not args.visualizations_only:
        print("Using static scenes mode - will process all predefined scenes")
    
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
        pipeline = MediaGenerationPipeline(config, use_static_scenes=args.static_scenes)
    except Exception as e:
        print(f"Error initializing pipeline: {e}")
        return 1
    
    # Run pipeline based on arguments
    try:
        if args.single and args.static_scenes:
            # Process single scene (static mode only)
            results = pipeline.generate_single_scene(args.single)
        elif args.content_only:
            # Generate content only
            if args.topic and not args.static_scenes:
                pipeline.scene_manager.generate_scenes(args.topic, args.num_scenes)
            results = pipeline.generate_content(args.scenes)
        elif args.visualizations_only:
            # Create visualizations only
            dummy_results = {}  # This would need existing content
            results = pipeline.create_visualizations(dummy_results)
        else:
            # Run complete pipeline
            results = pipeline.run_complete_pipeline(
                topic=args.topic if not args.static_scenes else None,
                scene_ids=args.scenes,
                num_scenes=args.num_scenes
            )
        
        print("\nPipeline completed successfully!")
        return 0
        
    except Exception as e:
        print(f"Error running pipeline: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 