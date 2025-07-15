"""
Scene Management module for the Media Generation Pipeline.
Handles scene definitions, prompts, and scene-related operations.
"""

from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class Scene:
    """Represents a single scene in the video generation pipeline."""
    id: str
    name: str
    prompt: str
    narration: str = ""
    image_file: str = ""
    
class SceneManager:
    """Manages all scenes in the video generation pipeline."""
    
    def __init__(self):
        self.scenes = self._initialize_scenes()
    
    def _initialize_scenes(self) -> Dict[str, Scene]:
        """Initialize all scenes with their prompts."""
        scenes_data = {
            "Scene 1": {
                "name": "The Stochastic Parrot",
                "prompt": "Generate an abstract digital artwork with swirling, chaotic data patterns in a neon-infused, cosmic style. In the center, display a brightly colored parrot with vivid, detailed plumage and a slightly open beak, as if squawking random, abstract phrases (incorporate subtle text elements like 'AI' and 'stochastic'). Use minimalistic line art mixed with dynamic color gradients and subtle motion blur. Reference the vibe of https://youtu.be/Tt5xNKojMvk but reinterpret it in a unique style."
            },
            "Scene 2": {
                "name": "Life as a Complex Stochastic Parrot",
                "prompt": "Evolve the previous scene by fading the parrot into a transition where abstract data flows morph into organic, cell-like structures. Gradually reveal macro shots of nature: a branching tree, a gently flowing river, and an intricately detailed ecosystem. Use soft pastel tones with natural textures to blend the abstract with the real."
            },
            "Scene 3": {
                "name": "Evolution and Functional Information",
                "prompt": "Create a dynamic visualization inspired by Darwin's theory of evolution: start with simple, varying silhouettes that transform under environmental pressures. Transition into an abstract display of self-organizing elements—scattered shapes coalescing into ordered patterns. Emphasize graphical elements to symbolize 'the second arrow of time' and increasing functional information, rendered in a clean, infographic style with surreal textures."
            },
            "Scene 4": {
                "name": "The AI Pipeline – Orchestrating the Agents",
                "prompt": "Generate a modern, technical diagram of an AI pipeline with distinct, labeled boxes for 'Data Ingestion,' 'Structure Analysis,' 'Content Enhancement,' 'Knowledge Extraction,' and 'Context Fusion' connected by smooth, glowing arrows. Render in a minimal, high-tech style with clean lines and subtle neon highlights."
            },
            "Scene 5": {
                "name": "Zooming In – The Alchemist Tribe (Anime Style)",
                "prompt": "Transform the clean pipeline diagram into an anime-style scene depicting an imaginative alchemist workshop. Show whimsical AI agents as dynamic anime characters (e.g., Docling, Slide Whisperer, Transcript Weaver) working with magical digital artifacts. Use vibrant, expressive colors, dynamic angles, and detailed line art with animated sparkles and lens flares."
            },
            "Scene 6": {
                "name": "The Alchemist Tribe's Story (Anime Short)",
                "prompt": "Develop a storyboard sequence in anime style with five interconnected scenes: (1) Raw educational materials flood into the workshop; (2) Close-ups of characters like Docling, Slide Whisperer, and Transcript Weaver; (3) A quadrant layout showing the four alchemical stages: Nigredo (black), Albedo (white), Citrinitas (yellow), Rubedo (red); (4) Collaborative energy with dynamic particle effects; (5) Refined output flowing towards a mysterious grand building. Include smooth transitions (pans/zooms) between quadrants."
            },
            "Scene 7": {
                "name": "Teaser and Perspective Shift",
                "prompt": "Create a cinematic transition where the anime scene shrinks into an inset screen on a large, dimly lit control room monitor. In the background, depict a realistic, high-tech room with multiple screens showing video lessons and metrics. Use a cinematic style with dramatic lighting and a dark, moody palette. Overlay a title card: 'Next Episode: The Scholar's Tribe'."
            },
            "Scene 8": {
                "name": "The Supervisor's Question",
                "prompt": "Generate a close-up cinematic portrait of a supervisor in a dark, technology-filled control room. The supervisor turns directly toward the viewer with a confident, challenging expression. Include a subtle text overlay or speech bubble that reads, 'So, how do you like it so far?' Render in a hyper-realistic, cinematic style with soft directional lighting and shallow depth of field."
            }
        }
        
        scenes = {}
        for scene_id, data in scenes_data.items():
            scenes[scene_id] = Scene(
                id=scene_id,
                name=data["name"],
                prompt=data["prompt"]
            )
        
        return scenes
    
    def get_scene(self, scene_id: str) -> Scene:
        """Get a specific scene by ID."""
        return self.scenes.get(scene_id)
    
    def get_all_scenes(self) -> Dict[str, Scene]:
        """Get all scenes."""
        return self.scenes
    
    def get_scene_ids(self) -> List[str]:
        """Get all scene IDs."""
        return list(self.scenes.keys())
    
    def update_scene_results(self, scene_id: str, narration: str = "", image_file: str = ""):
        """Update scene with generated results."""
        if scene_id in self.scenes:
            if narration:
                self.scenes[scene_id].narration = narration
            if image_file:
                self.scenes[scene_id].image_file = image_file
    
    def get_scene_summary(self) -> str:
        """Get a summary of all scenes."""
        summary = "Scene Summary:\n"
        for scene_id, scene in self.scenes.items():
            summary += f"  {scene_id}: {scene.name}\n"
        return summary 