"""
Scene extraction and description module using Computer Vision techniques.
This module extracts frames from videos and generates descriptions using pre-trained models.
"""

import os
import cv2
import numpy as np
import torch
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from typing import List, Dict, Tuple, Optional

class SceneExtractor:
    """
    Extracts frames from videos and generates descriptions using computer vision models.
    """
    
    def __init__(self, model_name: str = "Salesforce/blip-image-captioning-base"):
        """
        Initialize the scene extractor with the specified image captioning model.
        
        Args:
            model_name: The name of the pre-trained model to use for image captioning
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"Loading image captioning model {model_name} on {self.device}...")
        self.processor = BlipProcessor.from_pretrained(model_name)
        self.model = BlipForConditionalGeneration.from_pretrained(model_name).to(self.device)
        print("Model loaded successfully!")
        
    def extract_frames(self, video_path: str, interval_seconds: int = 10, max_frames: int = 10, task_id: str = None) -> List[Dict]:
        """
        Extract frames from a video at regular intervals.
        
        Args:
            video_path: Path to the video file
            interval_seconds: Interval between frames in seconds
            max_frames: Maximum number of frames to extract
            task_id: Optional task ID to use in the frame directory name
            
        Returns:
            List of dictionaries containing frame data with timestamps and file paths
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        # Create a permanent directory for frames in the static folder
        static_frames_dir = '/home/jose/NLP_CV_Final_Project/app/static/frames'
        os.makedirs(static_frames_dir, exist_ok=True)
        
        # Create a task-specific directory for frames
        video_name = os.path.basename(video_path).split('.')[0]
        task_prefix = f"{task_id[:8]}_" if task_id else ""
        frames_dir = os.path.join(static_frames_dir, f"{task_prefix}{video_name}")
        os.makedirs(frames_dir, exist_ok=True)
        
        # Open the video file
        video = cv2.VideoCapture(video_path)
        if not video.isOpened():
            raise Exception(f"Could not open video file: {video_path}")
        
        # Get video properties
        fps = video.get(cv2.CAP_PROP_FPS)
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        print(f"Video properties: FPS={fps}, Duration={duration}s, Total frames={total_frames}")
        
        # Calculate frame extraction positions
        interval_frames = int(fps * interval_seconds)
        frame_positions = []
        
        current_frame = 0
        while current_frame < total_frames and len(frame_positions) < max_frames:
            frame_positions.append(current_frame)
            current_frame += interval_frames
        
        # Extract frames
        frames = []
        for i, frame_pos in enumerate(frame_positions):
            video.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            success, frame = video.read()
            if not success:
                continue
            
            timestamp = frame_pos / fps
            frame_filename = f"frame_{i:03d}_{int(timestamp)}s.jpg"
            frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(frame_path, frame)
            
            # Create a URL path that can be accessed via the /static route
            frame_url_path = f"/static/frames/{task_prefix}{video_name}/{frame_filename}"
            
            frames.append({
                "index": i,
                "timestamp": timestamp,
                "timestamp_formatted": self._format_timestamp(timestamp),
                "path": frame_path,
                "url": frame_url_path
            })
        
        video.release()
        print(f"Extracted {len(frames)} frames from video")
        return frames
    
    def describe_frames(self, frames: List[Dict]) -> List[Dict]:
        """
        Generate descriptions for a list of video frames.
        
        Args:
            frames: List of frame dictionaries with paths
            
        Returns:
            Updated list of frame dictionaries with descriptions
        """
        for frame in frames:
            frame_path = frame["path"]
            if not os.path.exists(frame_path):
                frame["description"] = "Frame image not found"
                continue
            
            # Load and process the image
            image = Image.open(frame_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt").to(self.device)
            
            # Generate caption
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs, 
                    max_length=50,
                    do_sample=True,
                    top_k=50,
                    top_p=0.95
                )
            
            # Decode the generated caption
            generated_text = self.processor.decode(outputs[0], skip_special_tokens=True)
            
            frame["description"] = generated_text
            
        return frames
    
    def extract_and_describe(self, video_path: str, interval_seconds: int = 10, max_frames: int = 10, task_id: str = None) -> List[Dict]:
        """
        Extract frames from a video and generate descriptions.
        
        Args:
            video_path: Path to the video file
            interval_seconds: Interval between frames in seconds
            max_frames: Maximum number of frames to extract
            task_id: Optional task ID to use in the frame directory name
            
        Returns:
            List of dictionaries containing frame data with timestamps, file paths, and descriptions
        """
        frames = self.extract_frames(video_path, interval_seconds, max_frames, task_id)
        return self.describe_frames(frames)
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        Format a timestamp in seconds to a human-readable format (MM:SS).
        
        Args:
            seconds: Timestamp in seconds
            
        Returns:
            Formatted timestamp string
        """
        minutes = int(seconds // 60)
        remaining_seconds = int(seconds % 60)
        return f"{minutes:02d}:{remaining_seconds:02d}"
