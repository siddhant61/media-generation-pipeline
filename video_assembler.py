"""
Video Assembly module for the Media Generation Pipeline.
Handles combining images and audio into final MP4 videos.
"""

import os
from typing import List, Optional
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
from PIL import Image

from config import config
from scene_manager import Scene


class VideoAssembler:
    """Assembles final video from generated images and audio."""
    
    def __init__(self, api_config=None):
        """Initialize the video assembler."""
        self.config = api_config or config
        self.output_dir = self.config.output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        print("Video Assembler initialized successfully!")
    
    def create_video_from_scenes(self, 
                                 scenes: List[Scene], 
                                 output_filename: str = "final_video.mp4",
                                 fps: int = 24,
                                 default_duration: float = 5.0) -> str:
        """
        Create a video from a list of scenes with synchronized audio.
        
        Args:
            scenes: List of Scene objects with image_file and audio_file paths
            output_filename: Name of the output video file
            fps: Frames per second for the video
            default_duration: Default duration in seconds if no audio is available
            
        Returns:
            Path to the generated video file
        """
        try:
            if not scenes:
                print("No scenes provided for video creation")
                return ""
            
            print(f"\n=== VIDEO ASSEMBLY ===")
            print(f"Creating video from {len(scenes)} scenes...")
            
            clips = []
            
            for idx, scene in enumerate(scenes, 1):
                print(f"Processing scene {idx}/{len(scenes)}: {scene.name}")
                
                # Validate image file exists
                if not scene.image_file or not os.path.exists(scene.image_file):
                    print(f"Warning: Image file not found for {scene.name}, skipping...")
                    continue
                
                # Determine duration from audio or use default
                duration = default_duration
                audio_clip = None
                
                if scene.audio_file and os.path.exists(scene.audio_file):
                    try:
                        audio_clip = AudioFileClip(scene.audio_file)
                        duration = audio_clip.duration
                        print(f"  Audio duration: {duration:.2f}s")
                    except Exception as e:
                        print(f"  Warning: Could not load audio for {scene.name}: {e}")
                        audio_clip = None
                else:
                    print(f"  No audio file, using default duration: {duration}s")
                
                # Create image clip
                try:
                    # Load image to get dimensions
                    img = Image.open(scene.image_file)
                    img_width, img_height = img.size
                    
                    # Create image clip with specified duration
                    image_clip = ImageClip(scene.image_file, duration=duration)
                    
                    # Set the audio if available
                    if audio_clip:
                        image_clip = image_clip.set_audio(audio_clip)
                    
                    # Set fps
                    image_clip = image_clip.set_fps(fps)
                    
                    clips.append(image_clip)
                    print(f"  Clip created: {duration:.2f}s, {img_width}x{img_height}")
                    
                except Exception as e:
                    print(f"  Error creating clip for {scene.name}: {e}")
                    continue
            
            if not clips:
                print("No valid clips to assemble")
                return ""
            
            print(f"\nConcatenating {len(clips)} clips...")
            
            # Concatenate all clips
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Set output path
            output_path = os.path.join(self.output_dir, output_filename)
            
            # Write video file
            print(f"Writing video to {output_path}...")
            final_clip.write_videofile(
                output_path,
                fps=fps,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile='temp-audio.m4a',
                remove_temp=True,
                logger='bar'
            )
            
            # Close all clips to free resources
            final_clip.close()
            for clip in clips:
                clip.close()
            
            print(f"Video successfully created: {output_path}")
            print(f"Total duration: {sum(c.duration for c in clips):.2f}s")
            
            return output_path
            
        except Exception as e:
            print(f"Error creating video: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def create_video_with_text_overlays(self,
                                        scenes: List[Scene],
                                        image_processor,
                                        output_filename: str = "final_video.mp4",
                                        fps: int = 24,
                                        default_duration: float = 5.0) -> str:
        """
        Create a video with text overlays applied to images before assembly.
        
        Args:
            scenes: List of Scene objects
            image_processor: ImageProcessor instance for adding overlays
            output_filename: Name of the output video file
            fps: Frames per second
            default_duration: Default duration if no audio
            
        Returns:
            Path to the generated video file
        """
        print("Adding text overlays to scenes before video creation...")
        
        # Create scenes with overlaid images
        scenes_with_overlays = []
        
        for scene in scenes:
            if scene.image_file and os.path.exists(scene.image_file):
                # Add text overlay
                overlay_path = image_processor.add_text_overlay(
                    scene.image_file,
                    scene.name,
                    position='bottom'
                )
                
                # Create a copy of the scene with the overlay image
                from dataclasses import replace
                scene_copy = replace(scene, image_file=overlay_path)
                scenes_with_overlays.append(scene_copy)
            else:
                scenes_with_overlays.append(scene)
        
        # Create video with overlay images
        return self.create_video_from_scenes(
            scenes_with_overlays,
            output_filename,
            fps,
            default_duration
        )
