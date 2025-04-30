import streamlit as st
import os
import json
import time
import tempfile
import requests
import subprocess
import torch
import numpy as np
import cv2
import nltk
from pytube import YouTube
import whisper
from transformers import pipeline, MarianMTModel, MarianTokenizer
from PIL import Image

# Download NLTK data if needed
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

# Helper functions for transcription
def download_youtube_video(url, output_dir):
    """Download a YouTube video to the specified directory."""
    try:
        # Extract video ID from URL
        if 'youtu.be' in url:
            video_id = url.split('/')[-1].split('?')[0]
        elif 'youtube.com/watch' in url:
            from urllib.parse import parse_qs, urlparse
            parsed_url = urlparse(url)
            video_id = parse_qs(parsed_url.query).get('v', [None])[0]
        else:
            video_id = None
            
        if not video_id:
            raise Exception("Could not extract video ID from URL")
            
        # Create YouTube object with specific parameters to avoid API issues
        yt = YouTube(
            url,
            use_oauth=False,
            allow_oauth_cache=False
        )
        
        # Get highest quality MP4 stream
        video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        
        if not video:
            # Try getting any video stream if progressive MP4 is not available
            video = yt.streams.filter(file_extension='mp4').first()
            
        if not video:
            raise Exception("No suitable video stream found")
            
        # Download the video
        output_path = video.download(output_path=output_dir)
        return output_path, yt.title
    except Exception as e:
        st.error(f"YouTube download error: {str(e)}")
        st.info("If YouTube download fails, please try the 'Upload Video File' option instead.")
        raise Exception(f"Error downloading YouTube video: {str(e)}")

        
# Alternative function that works with video file URLs
def process_video_url(url, output_dir):
    """Process a direct video file URL (not YouTube)."""
    try:
        # Download the video file directly
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(output_dir, "video.mp4")
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):
                    if chunk:
                        f.write(chunk)
            return file_path, "Downloaded Video"
        else:
            raise Exception(f"Failed to download video: HTTP {response.status_code}")
    except Exception as e:
        raise Exception(f"Error downloading video: {str(e)}")


def transcribe_video(video_path, model_size='base'):
    """Transcribe a video file using Whisper."""
    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(video_path)
        return result["text"]
    except Exception as e:
        raise Exception(f"Error transcribing video: {str(e)}")

# Helper functions for script generation
def structure_transcript(transcript):
    """Structure the transcript into sections."""
    # Define section patterns
    sections = [
        {"title": "Hook", "description": "Attention-grabbing opening", "content": ""},
        {"title": "Introduction", "description": "Topic and purpose introduction", "content": ""},
        {"title": "Main Content", "description": "Core information and details", "content": ""},
        {"title": "Call to Action", "description": "Engagement request", "content": ""},
        {"title": "Outro", "description": "Closing remarks", "content": ""}
    ]
    
    # Simple algorithm to divide transcript into sections
    sentences = nltk.sent_tokenize(transcript)
    total_sentences = len(sentences)
    
    # Distribute sentences to sections
    hook_end = max(1, int(total_sentences * 0.1))  # 10% for hook
    intro_end = hook_end + max(1, int(total_sentences * 0.15))  # 15% for intro
    cta_start = max(intro_end + 1, int(total_sentences * 0.85))  # 15% for CTA and outro combined
    outro_start = max(cta_start + 1, int(total_sentences * 0.92))  # Last 8% for outro
    
    sections[0]["content"] = " ".join(sentences[:hook_end])
    sections[1]["content"] = " ".join(sentences[hook_end:intro_end])
    sections[2]["content"] = " ".join(sentences[intro_end:cta_start])
    sections[3]["content"] = " ".join(sentences[cta_start:outro_start])
    sections[4]["content"] = " ".join(sentences[outro_start:])
    
    return {"sections": sections}

def translate_to_spanish(text):
    """Translate text from English to Spanish using MarianMT."""
    try:
        model_name = "Helsinki-NLP/opus-mt-en-es"
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        
        # Split text into chunks to avoid token limit issues
        max_length = 512
        sentences = nltk.sent_tokenize(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(tokenizer.encode(current_chunk + " " + sentence)) <= max_length:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                chunks.append(current_chunk)
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk)
        
        # Translate each chunk
        translated_chunks = []
        for chunk in chunks:
            inputs = tokenizer(chunk, return_tensors="pt", padding=True, truncation=True, max_length=max_length)
            with torch.no_grad():
                output = model.generate(**inputs)
            translated_text = tokenizer.decode(output[0], skip_special_tokens=True)
            translated_chunks.append(translated_text)
        
        return " ".join(translated_chunks)
    except Exception as e:
        raise Exception(f"Error translating text: {str(e)}")

def generate_structured_scripts(transcript):
    """Generate structured scripts in English and Spanish."""
    # Structure the original transcript
    structured_transcript = structure_transcript(transcript)
    
    # Create Spanish version with the same structure
    spanish_sections = []
    for section in structured_transcript["sections"]:
        spanish_content = translate_to_spanish(section["content"])
        spanish_sections.append({
            "title": section["title"],
            "description": section["description"],
            "content": spanish_content
        })
    
    spanish_script = {"sections": spanish_sections}
    
    return {
        "original": structured_transcript,
        "spanish": spanish_script
    }

# Helper functions for scene extraction
def extract_frames(video_path, interval_seconds=30, max_frames=6):
    """Extract frames from a video at regular intervals."""
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Error opening video file")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        # Calculate frame positions
        interval_frames = int(interval_seconds * fps)
        frame_positions = []
        
        if duration <= interval_seconds * max_frames:
            # For short videos, distribute frames evenly
            for i in range(min(max_frames, int(duration / interval_seconds) + 1)):
                frame_positions.append(int(i * interval_frames))
        else:
            # For longer videos, take frames at regular intervals
            for i in range(max_frames):
                position = int(i * (total_frames / max_frames))
                frame_positions.append(position)
        
        # Extract frames
        frames = []
        for position in frame_positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, position)
            ret, frame = cap.read()
            if ret:
                # Convert BGR to RGB for PIL
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                timestamp = position / fps
                frames.append({
                    "frame": frame_rgb,
                    "timestamp": timestamp,
                    "timestamp_formatted": time.strftime("%H:%M:%S", time.gmtime(timestamp))
                })
        
        cap.release()
        return frames
    except Exception as e:
        raise Exception(f"Error extracting frames: {str(e)}")

def describe_image(image):
    """Generate a description for an image using a pre-trained model."""
    try:
        # Use a simpler image captioning model for Streamlit deployment
        captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
        pil_image = Image.fromarray(image)
        result = captioner(pil_image)
        return result[0]["generated_text"]
    except Exception as e:
        return f"Could not generate description: {str(e)}"

def extract_and_describe_scenes(video_path, interval_seconds=30, max_frames=6):
    """Extract frames from a video and generate descriptions."""
    frames = extract_frames(video_path, interval_seconds, max_frames)
    scenes = []
    
    for frame_data in frames:
        # Save frame to a temporary file
        temp_dir = tempfile.mkdtemp()
        frame_path = os.path.join(temp_dir, f"frame_{frame_data['timestamp']}.jpg")
        Image.fromarray(frame_data["frame"]).save(frame_path)
        
        # Generate description
        description = describe_image(frame_data["frame"])
        
        scenes.append({
            "timestamp": frame_data["timestamp"],
            "timestamp_formatted": frame_data["timestamp_formatted"],
            "description": description,
            "frame_path": frame_path
        })
    
    return scenes

# Helper functions for prompt generation
def generate_image_prompt(scene_description):
    """Generate an AI image prompt based on a scene description."""
    prompt = f"Create a detailed image of: {scene_description}. Use high-quality lighting, detailed textures, and a cinematic composition."
    return prompt

def generate_video_prompt(scene_description):
    """Generate an AI video prompt based on a scene description."""
    prompt = f"Create a 5-second video clip showing: {scene_description}. Include smooth camera movement, realistic lighting, and natural motion."
    return prompt

def generate_prompts_for_scenes(scenes):
    """Generate AI prompts for a list of scenes."""
    scenes_with_prompts = []
    
    for scene in scenes:
        scene_with_prompts = scene.copy()
        scene_with_prompts["image_prompt"] = generate_image_prompt(scene["description"])
        scene_with_prompts["video_prompt"] = generate_video_prompt(scene["description"])
        scenes_with_prompts.append(scene_with_prompts)
    
    return scenes_with_prompts

# Set page config
st.set_page_config(
    page_title="Video Content Adaptation System",
    page_icon="🎬",
    layout="wide"
)

# Title and description
st.title("Video Content Adaptation System")
st.markdown("""
This application combines NLP and Computer Vision to:
1. Transcribe videos in any language
2. Create Spanish scripts with proper structure
3. Extract scene descriptions using Computer Vision
4. Generate AI image/video prompts
""")

# Input options
input_option = st.radio(
    "Choose input method:",
    ("YouTube URL", "Upload Video File")
)

if input_option == "YouTube URL":
    st.info("Enter a YouTube URL to process. Examples: https://www.youtube.com/watch?v=dQw4w9WgXcQ or https://youtu.be/dQw4w9WgXcQ")
    youtube_url = st.text_input("Enter YouTube URL:")
    
    # Sample YouTube URLs
    st.markdown("**Sample YouTube URLs you can try:**")
    st.code("https://www.youtube.com/watch?v=dQw4w9WgXcQ", language="text")
    st.code("https://youtu.be/9bZkp7q19f0", language="text")
    
    process_button = st.button("Process YouTube Video")
    
    if process_button and youtube_url:
        with st.spinner("Processing YouTube video... This may take a few minutes."):
            try:
                # Create a temporary directory for processing
                temp_dir = tempfile.mkdtemp()
                
                # Download YouTube video
                st.text("Downloading video from YouTube...")
                video_path, video_title = download_youtube_video(youtube_url, temp_dir)
                st.text(f"Downloaded: {video_title}")
                
                # Show success message with video title
                st.success(f"Successfully downloaded: {video_title}")


                
                # Transcribe video
                st.text("Transcribing video...")
                transcript = transcribe_video(video_path)
                
                # Generate scripts
                st.text("Generating scripts...")
                structured_scripts = generate_structured_scripts(transcript)
                structured_transcript = structured_scripts["original"]
                spanish_script = structured_scripts["spanish"]
                
                # Extract scenes
                st.text("Extracting scenes...")
                scenes = extract_and_describe_scenes(video_path)
                
                # Generate prompts
                st.text("Generating AI prompts...")
                scenes_with_prompts = generate_prompts_for_scenes(scenes)
                
                # Display results
                st.success("Processing complete!")
                
                # Display transcript
                st.header("Video Transcript")
                for section in structured_transcript["sections"]:
                    with st.expander(f"{section['title']} - {section['description']}"):
                        st.write(section["content"])
                
                # Display Spanish script
                st.header("Spanish Video Script")
                for section in spanish_script["sections"]:
                    with st.expander(f"{section['title']} - {section['description']}"):
                        st.write(section["content"])
                
                # Display scenes
                st.header("Scene Descriptions")
                cols = st.columns(3)
                for i, scene in enumerate(scenes_with_prompts):
                    with cols[i % 3]:
                        st.subheader(f"Scene at {scene['timestamp_formatted']}")
                        if 'frame_path' in scene and os.path.exists(scene['frame_path']):
                            st.image(scene['frame_path'])
                        st.write(scene["description"])
                        with st.expander("AI Image Prompt"):
                            st.code(scene["image_prompt"])
                        with st.expander("AI Video Prompt"):
                            st.code(scene["video_prompt"])
            
            except Exception as e:
                st.error(f"Error processing video: {str(e)}")

else:  # Upload Video File
    uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi", "mkv"])
    process_button = st.button("Process Video")
    
    if process_button and uploaded_file:
        with st.spinner("Processing video... This may take a few minutes."):
            try:
                # Create a temporary directory and save the uploaded file
                temp_dir = tempfile.mkdtemp()
                temp_path = os.path.join(temp_dir, uploaded_file.name)
                
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Transcribe video
                st.text("Transcribing video...")
                transcript = transcribe_video(temp_path)
                
                # Generate scripts
                st.text("Generating scripts...")
                structured_scripts = generate_structured_scripts(transcript)
                structured_transcript = structured_scripts["original"]
                spanish_script = structured_scripts["spanish"]
                
                # Extract scenes
                st.text("Extracting scenes...")
                scenes = extract_and_describe_scenes(temp_path)
                
                # Generate prompts
                st.text("Generating AI prompts...")
                scenes_with_prompts = generate_prompts_for_scenes(scenes)
                
                # Display results
                st.success("Processing complete!")
                
                # Display transcript
                st.header("Video Transcript")
                for section in structured_transcript["sections"]:
                    with st.expander(f"{section['title']} - {section['description']}"):
                        st.write(section["content"])
                
                # Display Spanish script
                st.header("Spanish Video Script")
                for section in spanish_script["sections"]:
                    with st.expander(f"{section['title']} - {section['description']}"):
                        st.write(section["content"])
                
                # Display scenes
                st.header("Scene Descriptions")
                cols = st.columns(3)
                for i, scene in enumerate(scenes_with_prompts):
                    with cols[i % 3]:
                        st.subheader(f"Scene at {scene['timestamp_formatted']}")
                        if 'frame_path' in scene and os.path.exists(scene['frame_path']):
                            st.image(scene['frame_path'])
                        st.write(scene["description"])
                        with st.expander("AI Image Prompt"):
                            st.code(scene["image_prompt"])
                        with st.expander("AI Video Prompt"):
                            st.code(scene["video_prompt"])
            
            except Exception as e:
                st.error(f"Error processing video: {str(e)}")

# Footer
st.markdown("---")
st.markdown("© 2025 Video Content Adaptation System | NLP + CV Final Project")

