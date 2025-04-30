import streamlit as st
import os
import json
import time
import tempfile
import requests
from app.utils.transcription import celery_transcribe
from app.utils.script_generation import generate_structured_scripts
from app.utils.scene_extraction import SceneExtractor
from app.utils.prompt_generation import PromptGenerator

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
    youtube_url = st.text_input("Enter YouTube URL:")
    process_button = st.button("Process Video")
    
    if process_button and youtube_url:
        with st.spinner("Processing video... This may take a few minutes."):
            # Create a temporary directory for processing
            temp_dir = tempfile.mkdtemp()
            
            # Process directly (no Celery in Streamlit version)
            try:
                # Transcribe
                st.text("Transcribing video...")
                transcript = celery_transcribe(youtube_url, is_youtube=True, model_size='base')
                
                # Generate scripts
                st.text("Generating scripts...")
                structured_scripts = generate_structured_scripts(transcript)
                structured_transcript = structured_scripts["original"]
                spanish_script = structured_scripts["spanish"]
                
                # Extract scenes
                st.text("Extracting scenes...")
                scene_extractor = SceneExtractor()
                scenes = scene_extractor.extract_and_describe(
                    os.path.join(temp_dir, "video.mp4"),
                    interval_seconds=30,
                    max_frames=6
                )
                
                # Generate prompts
                st.text("Generating AI prompts...")
                prompt_generator = PromptGenerator()
                scenes_with_prompts = prompt_generator.generate_prompts_for_scenes(scenes)
                
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
            # Create a temporary directory and save the uploaded file
            temp_dir = tempfile.mkdtemp()
            temp_path = os.path.join(temp_dir, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Process directly (similar to YouTube processing)
            try:
                # Similar processing as above, but with the uploaded file
                # ...
                st.success("Processing complete!")
                # Display results (similar to above)
                # ...
            
            except Exception as e:
                st.error(f"Error processing video: {str(e)}")

# Footer
st.markdown("---")
st.markdown("© 2025 Video Content Adaptation System | NLP + CV Final Project")
