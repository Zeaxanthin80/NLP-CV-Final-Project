"""
AI Prompt Generation Module.
This module generates AI image and video prompts from scene descriptions.
"""

import re
import random
from typing import List, Dict, Any, Optional

class PromptGenerator:
    """
    Generates AI image and video prompts from scene descriptions.
    """
    
    def __init__(self):
        """
        Initialize the prompt generator with style templates and enhancement phrases.
        """
        # Style templates for different visual aesthetics
        self.style_templates = [
            "photorealistic, detailed, 8k resolution, professional photography",
            "cinematic, dramatic lighting, movie still, depth of field",
            "vibrant colors, sharp details, professional videography",
            "artistic, stylized, professional composition, high quality",
            "documentary style, natural lighting, authentic",
            "studio quality, professional lighting, high production value"
        ]
        
        # Enhancement phrases to add detail and context
        self.enhancement_phrases = {
            "lighting": [
                "soft natural lighting", "dramatic side lighting", 
                "golden hour sunlight", "blue hour ambient light",
                "studio lighting setup", "dramatic shadows",
                "backlit with rim light", "overhead lighting"
            ],
            "camera": [
                "wide-angle shot", "close-up shot", 
                "medium shot", "aerial view",
                "low angle perspective", "high angle perspective",
                "shallow depth of field", "deep focus"
            ],
            "mood": [
                "professional atmosphere", "casual setting", 
                "energetic mood", "calm and serene",
                "tense moment", "joyful scene",
                "serious tone", "inspirational feeling"
            ],
            "quality": [
                "highly detailed", "professional quality", 
                "8K resolution", "crystal clear",
                "sharp focus", "cinematic quality",
                "studio quality", "broadcast ready"
            ]
        }
        
        # Keywords to detect scene types
        self.scene_keywords = {
            "interview": ["interview", "talking", "speaking", "conversation"],
            "presentation": ["presentation", "slide", "conference", "lecture"],
            "outdoor": ["outdoor", "nature", "landscape", "sky", "outside"],
            "action": ["action", "moving", "running", "walking", "activity"],
            "product": ["product", "device", "gadget", "technology", "item"],
            "group": ["group", "people", "crowd", "audience", "team"]
        }
    
    def enhance_description(self, description: str) -> str:
        """
        Enhance a basic scene description with more details.
        
        Args:
            description: The original scene description
            
        Returns:
            Enhanced description with more details
        """
        # Clean the description
        description = description.strip().lower()
        if not description or description == "no description available":
            return "A professional video scene with good lighting and composition"
        
        # Remove any non-descriptive phrases
        description = re.sub(r'(image of|picture of|photo of|showing|depicting)', '', description)
        
        # Determine scene type based on keywords
        scene_type = "general"
        for stype, keywords in self.scene_keywords.items():
            if any(keyword in description for keyword in keywords):
                scene_type = stype
                break
        
        # Add enhancements based on scene type
        enhancements = []
        
        # Always add quality enhancement
        enhancements.append(random.choice(self.enhancement_phrases["quality"]))
        
        # Add lighting enhancement
        enhancements.append(random.choice(self.enhancement_phrases["lighting"]))
        
        # Add camera enhancement
        enhancements.append(random.choice(self.enhancement_phrases["camera"]))
        
        # Add mood enhancement for certain scene types
        if scene_type in ["interview", "presentation", "group"]:
            enhancements.append(random.choice(self.enhancement_phrases["mood"]))
        
        # Combine the original description with enhancements
        enhanced = f"{description}, {', '.join(enhancements)}"
        
        return enhanced
    
    def generate_image_prompt(self, scene: Dict[str, Any]) -> str:
        """
        Generate an AI image prompt from a scene description.
        
        Args:
            scene: Dictionary containing scene data
            
        Returns:
            AI image prompt string
        """
        description = scene.get("description", "")
        timestamp = scene.get("timestamp_formatted", "")
        
        # Enhance the basic description
        enhanced_desc = self.enhance_description(description)
        
        # Add a style template
        style = random.choice(self.style_templates)
        
        # Construct the final prompt
        prompt = f"{enhanced_desc}. {style}"
        
        return prompt
    
    def generate_video_prompt(self, scene: Dict[str, Any]) -> str:
        """
        Generate an AI video prompt from a scene description.
        
        Args:
            scene: Dictionary containing scene data
            
        Returns:
            AI video prompt string
        """
        # Start with the image prompt
        image_prompt = self.generate_image_prompt(scene)
        
        # Add video-specific elements
        video_elements = [
            "smooth camera movement",
            "15 second clip",
            "natural motion",
            "realistic movement",
            "professional video quality"
        ]
        
        # Add 2-3 random video elements
        selected_elements = random.sample(video_elements, k=min(3, len(video_elements)))
        
        # Construct the final video prompt
        prompt = f"{image_prompt}, {', '.join(selected_elements)}"
        
        return prompt
    
    def generate_prompts_for_scenes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate AI prompts for a list of scenes.
        
        Args:
            scenes: List of scene dictionaries
            
        Returns:
            List of scene dictionaries with added prompt fields
        """
        for scene in scenes:
            scene["image_prompt"] = self.generate_image_prompt(scene)
            scene["video_prompt"] = self.generate_video_prompt(scene)
        
        return scenes
