"""
Content Generation module for the Media Generation Pipeline.
Handles OpenAI narration generation and Stability AI image generation.
"""

import os
import io
from typing import Optional, Dict, Any
from openai import OpenAI
from stability_sdk import client
import stability_sdk.interfaces.gooseai.generation.generation_pb2 as generation
from PIL import Image as PILImage
import time

from config import config
from scene_manager import Scene

class ContentGenerator:
    """Handles content generation using OpenAI and Stability AI APIs."""
    
    def __init__(self, api_config=None):
        """Initialize the content generator with API clients."""
        self.config = api_config or config
        self.config.validate()
        
        # Initialize OpenAI client
        self.openai_client = OpenAI(api_key=self.config.openai_api_key)
        
        # Initialize Stability AI client
        self.stability_api = client.StabilityInference(
            key=self.config.stability_api_key,
            verbose=True
        )
        
        # Create output directory
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        print('Content Generator initialized successfully.')
    
    def generate_narration(self, scene: Scene) -> str:
        """
        Generate narration text for a scene using OpenAI.
        
        Args:
            scene: Scene object containing name and prompt
            
        Returns:
            Generated narration text
        """
        narration_prompt = f"""Generate a concise, engaging narration text for the scene '{scene.name}'. 
        The scene details are: {scene.prompt}
        
        The narration should be:
        - Engaging and suitable for video content
        - Approximately 30-60 seconds when spoken
        - Clear and easy to understand
        - Complementary to the visual content
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.config.openai_model,
                messages=[
                    {"role": "system", "content": "You are a skilled narrator and storyteller for educational video content."},
                    {"role": "user", "content": narration_prompt}
                ],
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature
            )
            
            narration = response.choices[0].message.content.strip()
            print(f'Generated narration for {scene.id}: {scene.name}')
            return narration
            
        except Exception as e:
            print(f'Error generating narration for {scene.id}: {e}')
            return f"Narration for {scene.name} - content not available due to generation error."
    
    def generate_image(self, scene: Scene, output_filename: Optional[str] = None) -> str:
        """
        Generate an image for a scene using Stability AI.
        
        Args:
            scene: Scene object containing prompt
            output_filename: Optional custom filename for output
            
        Returns:
            Path to the generated image file
        """
        if output_filename is None:
            output_filename = f"{scene.id.replace(' ', '_')}.png"
        
        output_path = os.path.join(self.config.output_dir, output_filename)
        
        try:
            print(f'Generating image for {scene.id}: {scene.name}')
            
            # Generate the image
            answers = self.stability_api.generate(
                prompt=scene.prompt,
                seed=self.config.stability_seed,
                steps=self.config.stability_steps,
                cfg_scale=self.config.stability_cfg_scale,
                width=self.config.stability_width,
                height=self.config.stability_height,
                samples=self.config.stability_samples,
                sampler=generation.SAMPLER_K_DPMPP_2M
            )
            
            # Process and save the image
            for answer in answers:
                for artifact in answer.artifacts:
                    if artifact.finish_reason == generation.FILTER:
                        print(f"Safety filter triggered for {scene.id}")
                        continue
                        
                    if artifact.type == generation.ARTIFACT_IMAGE:
                        img = PILImage.open(io.BytesIO(artifact.binary))
                        img.save(output_path)
                        print(f'Image saved as {output_path}')
                        return output_path
            
            print(f'No valid image generated for {scene.id}')
            return ""
            
        except Exception as e:
            print(f'Error generating image for {scene.id}: {e}')
            return ""
    
    def generate_scene_content(self, scene: Scene) -> Dict[str, Any]:
        """
        Generate both narration and image for a scene.
        
        Args:
            scene: Scene object
            
        Returns:
            Dictionary containing narration and image file path
        """
        print(f'Processing {scene.id}: {scene.name}')
        
        # Generate narration
        narration = self.generate_narration(scene)
        
        # Generate image
        image_file = self.generate_image(scene)
        
        # Add a small delay to avoid rate limiting
        time.sleep(1)
        
        return {
            'narration': narration,
            'image_file': image_file
        }
    
    def process_all_scenes(self, scenes: Dict[str, Scene]) -> Dict[str, Dict[str, Any]]:
        """
        Process all scenes to generate content.
        
        Args:
            scenes: Dictionary of Scene objects
            
        Returns:
            Dictionary containing results for all scenes
        """
        results = {}
        
        print(f'Processing {len(scenes)} scenes...')
        
        for scene_id, scene in scenes.items():
            result = self.generate_scene_content(scene)
            results[scene_id] = result
            
            # Update scene object with results
            scene.narration = result['narration']
            scene.image_file = result['image_file']
            
            print(f'Completed {scene_id}')
            print(f'Narration: {result["narration"][:100]}...\n')
        
        print('All scenes processed successfully.')
        return results 