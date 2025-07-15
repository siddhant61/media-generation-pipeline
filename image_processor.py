"""
Image Processing module for the Media Generation Pipeline.
Handles transitions, text overlays, storyboards, and animation creation.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import textwrap

from config import config

class ImageProcessor:
    """Handles image processing operations for the video generation pipeline."""
    
    def __init__(self, api_config=None):
        """Initialize the image processor."""
        self.config = api_config or config
        self.output_dir = self.config.output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create subdirectories for different types of outputs
        self.transitions_dir = os.path.join(self.output_dir, "transitions")
        self.overlays_dir = os.path.join(self.output_dir, "overlays")
        self.storyboards_dir = os.path.join(self.output_dir, "storyboards")
        
        for directory in [self.transitions_dir, self.overlays_dir, self.storyboards_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def generate_transition(self, scene1_img: str, scene2_img: str, num_frames: int = 5) -> List[str]:
        """
        Generate transition frames between two images.
        
        Args:
            scene1_img: Path to first image
            scene2_img: Path to second image
            num_frames: Number of transition frames to generate
            
        Returns:
            List of paths to generated transition frames
        """
        try:
            transition_frames = []
            
            # Load images
            img1 = Image.open(scene1_img).convert('RGBA')
            img2 = Image.open(scene2_img).convert('RGBA')
            
            # Ensure images are the same size
            if img1.size != img2.size:
                img2 = img2.resize(img1.size, Image.Resampling.LANCZOS)
            
            # Generate transition frames
            for i in range(num_frames):
                # Calculate blend factor (0 to 1)
                alpha = i / (num_frames - 1)
                
                # Create blended image
                blended = Image.blend(img1, img2, alpha)
                
                # Save frame
                frame_filename = f"transition_{os.path.basename(scene1_img)[:-4]}_to_{os.path.basename(scene2_img)[:-4]}_{i:02d}.png"
                frame_path = os.path.join(self.transitions_dir, frame_filename)
                blended.save(frame_path)
                transition_frames.append(frame_path)
            
            print(f'Generated {len(transition_frames)} transition frames')
            return transition_frames
            
        except Exception as e:
            print(f"Error generating transition: {e}")
            return []
    
    def add_text_overlay(self, 
                        image_path: str, 
                        text: str, 
                        position: str = 'bottom',
                        font_size: Optional[int] = None,
                        output_filename: Optional[str] = None) -> str:
        """
        Add text overlay to an image.
        
        Args:
            image_path: Path to the input image
            text: Text to overlay
            position: Position of text ('top', 'center', 'bottom')
            font_size: Font size for the text
            output_filename: Optional custom output filename
            
        Returns:
            Path to the image with text overlay
        """
        try:
            # Load image
            img = Image.open(image_path).convert('RGBA')
            
            # Create transparent overlay
            overlay = Image.new('RGBA', img.size, (255, 255, 255, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Set font
            if font_size is None:
                font_size = self.config.font_size
            
            # Try to load a font, fall back to default if not available
            try:
                font = ImageFont.truetype("arial.ttf", font_size)
            except OSError:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
                except OSError:
                    font = ImageFont.load_default()
                    font_size = 16
            
            # Calculate text wrapping
            max_width = img.width - 40  # 20px padding on each side
            avg_char_width = font_size * 0.6
            chars_per_line = int(max_width / avg_char_width)
            wrapped_text = textwrap.fill(text, width=chars_per_line)
            
            # Calculate text dimensions
            lines = wrapped_text.split('\n')
            line_height = font_size + 4
            text_height = len(lines) * line_height
            
            # Calculate position
            if position.lower() == 'top':
                y_start = 20
            elif position.lower() == 'center':
                y_start = (img.height - text_height) // 2
            else:  # bottom
                y_start = img.height - text_height - 20
            
            # Draw background rectangle
            padding = 10
            rect_top = y_start - padding
            rect_bottom = y_start + text_height + padding
            draw.rectangle([(0, rect_top), (img.width, rect_bottom)], fill=(0, 0, 0, 128))
            
            # Draw text
            current_y = y_start
            for line in lines:
                # Calculate text width for centering
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (img.width - text_width) // 2
                
                # Draw text with outline for better visibility
                outline_color = (0, 0, 0, 255)
                text_color = (255, 255, 255, 255)
                
                # Draw outline
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        if dx != 0 or dy != 0:
                            draw.text((x + dx, current_y + dy), line, font=font, fill=outline_color)
                
                # Draw main text
                draw.text((x, current_y), line, font=font, fill=text_color)
                current_y += line_height
            
            # Composite overlay onto original image
            result = Image.alpha_composite(img, overlay)
            
            # Save result
            if output_filename is None:
                output_filename = f"text_{os.path.basename(image_path)}"
            
            output_path = os.path.join(self.overlays_dir, output_filename)
            result.convert('RGB').save(output_path)
            
            print(f'Added text overlay to {os.path.basename(image_path)}')
            return output_path
            
        except Exception as e:
            print(f"Error adding text overlay: {e}")
            return image_path
    
    def create_storyboard(self, 
                         image_paths: List[str], 
                         captions: List[str], 
                         output_filename: str = "storyboard.png",
                         cols: int = 4) -> str:
        """
        Create a storyboard from multiple images.
        
        Args:
            image_paths: List of paths to images
            captions: List of captions for each image
            output_filename: Output filename for the storyboard
            cols: Number of columns in the storyboard
            
        Returns:
            Path to the generated storyboard
        """
        try:
            if not image_paths:
                print("No images provided for storyboard")
                return ""
            
            # Calculate grid dimensions
            n_images = len(image_paths)
            cols = min(cols, n_images)
            rows = (n_images + cols - 1) // cols
            
            # Image dimensions
            cell_width = 512
            cell_height = 612  # Extra space for captions
            
            # Create blank canvas
            canvas_width = cell_width * cols
            canvas_height = cell_height * rows
            canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))
            
            # Font for captions
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except OSError:
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
                except OSError:
                    font = ImageFont.load_default()
            
            # Place images and captions
            for idx, (img_path, caption) in enumerate(zip(image_paths, captions)):
                if idx >= n_images:
                    break
                
                # Calculate position
                row = idx // cols
                col = idx % cols
                x = col * cell_width
                y = row * cell_height
                
                try:
                    # Load and resize image
                    img = Image.open(img_path)
                    img = img.resize((cell_width, 512), Image.Resampling.LANCZOS)
                    
                    # Paste image
                    canvas.paste(img, (x, y))
                    
                    # Add caption
                    draw = ImageDraw.Draw(canvas)
                    caption_y = y + 512 + 10
                    
                    # Wrap caption text
                    wrapped_caption = textwrap.fill(caption, width=60)
                    lines = wrapped_caption.split('\n')
                    
                    for i, line in enumerate(lines):
                        draw.text((x + 10, caption_y + i * 25), line, font=font, fill=(0, 0, 0))
                
                except Exception as e:
                    print(f"Error processing image {img_path}: {e}")
                    continue
            
            # Save storyboard
            output_path = os.path.join(self.storyboards_dir, output_filename)
            canvas.save(output_path)
            
            print(f'Storyboard created: {output_path}')
            return output_path
            
        except Exception as e:
            print(f"Error creating storyboard: {e}")
            return ""
    
    def create_animated_gif(self, 
                           image_paths: List[str], 
                           output_filename: str = "animated_story.gif",
                           duration: int = 1000,
                           include_transitions: bool = True) -> str:
        """
        Create an animated GIF from a sequence of images.
        
        Args:
            image_paths: List of paths to images
            output_filename: Output filename for the GIF
            duration: Duration of each frame in milliseconds
            include_transitions: Whether to include transition frames
            
        Returns:
            Path to the generated animated GIF
        """
        try:
            if not image_paths:
                print("No images provided for animation")
                return ""
            
            frames = []
            
            # Load all images
            for i, img_path in enumerate(image_paths):
                try:
                    img = Image.open(img_path).convert('RGB')
                    frames.append(img)
                    
                    # Add transition frames if requested and not the last image
                    if include_transitions and i < len(image_paths) - 1:
                        next_img_path = image_paths[i + 1]
                        transition_frames = self.generate_transition(img_path, next_img_path, 3)
                        
                        for trans_frame_path in transition_frames:
                            trans_img = Image.open(trans_frame_path).convert('RGB')
                            frames.append(trans_img)
                
                except Exception as e:
                    print(f"Error loading image {img_path}: {e}")
                    continue
            
            if not frames:
                print("No valid frames for animation")
                return ""
            
            # Save as animated GIF
            output_path = os.path.join(self.output_dir, output_filename)
            frames[0].save(
                output_path,
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=0
            )
            
            print(f'Animated GIF created: {output_path}')
            return output_path
            
        except Exception as e:
            print(f"Error creating animated GIF: {e}")
            return "" 