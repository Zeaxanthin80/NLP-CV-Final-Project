import os
import tempfile
import subprocess
import json
from pytube import YouTube
import whisper
import traceback

# Download YouTube video and return the path to the downloaded file

def download_youtube_video(youtube_url, download_dir):
    """
    Downloads both video and audio from a YouTube URL using yt-dlp.
    Returns a tuple of (video_path, audio_path).
    """
    import shutil
    yt_dlp_path = shutil.which("yt-dlp")
    if not yt_dlp_path:
        raise RuntimeError("yt-dlp is not installed or not found in PATH.")
    
    # First, download the video file for scene extraction
    video_output_path = os.path.join(download_dir, 'video_%(title)s.%(ext)s')
    video_command = [
        yt_dlp_path,
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        '-o', video_output_path,
        youtube_url
    ]
    video_result = subprocess.run(video_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if video_result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed to download video: {video_result.stderr.decode('utf-8')}")
    
    # Find the downloaded video file
    video_path = None
    for fname in os.listdir(download_dir):
        if fname.startswith('video_') and (fname.endswith('.mp4') or fname.endswith('.mkv')):
            video_path = os.path.join(download_dir, fname)
            break
    
    if not video_path:
        raise RuntimeError("Video file not found after yt-dlp download.")
    
    # Now download/extract audio for transcription
    audio_output_path = os.path.join(download_dir, 'audio_%(title)s.%(ext)s')
    audio_command = [
        yt_dlp_path,
        '-f', 'bestaudio',
        '--extract-audio',
        '--audio-format', 'wav',
        '--audio-quality', '0',
        '-o', audio_output_path,
        youtube_url
    ]
    audio_result = subprocess.run(audio_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if audio_result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed to extract audio: {audio_result.stderr.decode('utf-8')}")
    
    # Find the downloaded audio file
    audio_path = None
    for fname in os.listdir(download_dir):
        if fname.startswith('audio_') and fname.endswith('.wav'):
            audio_path = os.path.join(download_dir, fname)
            break
    
    if not audio_path:
        raise RuntimeError("Audio file not found after yt-dlp download.")
    
    return (video_path, audio_path)

# Extract audio from video file using ffmpeg

def extract_audio(video_path, audio_path):
    command = [
        'ffmpeg', '-y', '-i', video_path,
        '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    return audio_path

# Transcribe audio using OpenAI Whisper

def transcribe_audio(audio_path, model_size='base'):
    model = whisper.load_model(model_size)
    result = model.transcribe(audio_path)
    return result['text']

# Main entry point for transcription
from celery import current_task
import redis

REDIS_URL = 'redis://localhost:6379/0'


def set_task_progress(task_id, progress, status_msg=None, result=None):
    """
    Set the progress of a task in Redis.
    
    Args:
        task_id: The ID of the task
        progress: The progress percentage (0-100)
        status_msg: A status message (optional)
        result: Optional result data
    """
    try:
        r = redis.Redis.from_url(REDIS_URL)
        task_key = f'celery-task-meta-{task_id}'
        
        # Check if the key exists and what type it is
        key_type = r.type(task_key).decode('utf-8')
        
        # If it's not a hash or doesn't exist, delete it and create a new hash
        if key_type != 'hash' and key_type != 'none':
            r.delete(task_key)
        
        # Create a data dictionary
        task_data = {'progress': progress}
        
        if status_msg:
            task_data['status_msg'] = status_msg
            
        if result:
            task_data['result'] = result
            # If we have a result and it's 100% complete, set status to success
            if progress == 100:
                task_data['status'] = 'success'
        
        # Store all data as a hash
        r.hset(task_key, mapping=task_data)
    except Exception as e:
        print(f"Error setting task progress: {str(e)}")

from app import create_app

from celery import shared_task

@shared_task(bind=True)
def celery_transcribe(self, source_path_or_url, is_youtube=False, model_size='base'):
    set_task_progress(self.request.id, 5, 'Starting transcription')
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            if is_youtube:
                set_task_progress(self.request.id, 10, 'Downloading YouTube video and audio')
                # Now returns a tuple of (video_path, audio_path)
                video_path, audio_path = download_youtube_video(source_path_or_url, tmpdir)
            else:
                set_task_progress(self.request.id, 10, 'Processing uploaded video')
                video_path = source_path_or_url
                audio_path = os.path.join(tmpdir, 'audio.wav')
                set_task_progress(self.request.id, 40, 'Extracting audio')
                extract_audio(video_path, audio_path)
                
            set_task_progress(self.request.id, 60, 'Transcribing audio')
            transcript = transcribe_audio(audio_path, model_size=model_size)
            
            # Generate Spanish script
            set_task_progress(self.request.id, 70, 'Generating Spanish script')
            try:
                from app.utils.script_generation import generate_spanish_script
                spanish_script = generate_spanish_script(transcript)
                # Ensure the script has the expected structure
                if not isinstance(spanish_script, dict) or 'sections' not in spanish_script:
                    spanish_script = {
                        "sections": {
                            "main_content": {
                                "title": "Contenido Principal",
                                "description": "Contenido traducido",
                                "content": "Error al estructurar el guión. Usando traducción simple."
                            }
                        }
                    }
                spanish_script_json = json.dumps(spanish_script)
            except Exception as e:
                print(f"Error generating Spanish script: {str(e)}")
                traceback.print_exc()
                # Create a valid JSON structure even on error
                spanish_script_json = json.dumps({
                    "sections": {
                        "error": {
                            "title": "Error",
                            "description": "Error al generar el guión en español",
                            "content": str(e)
                        }
                    }
                })
                
            # Extract and describe scenes from the video
            set_task_progress(self.request.id, 75, 'Extracting and describing scenes')
            try:
                from app.utils.scene_extraction import SceneExtractor
                scene_extractor = SceneExtractor()
                scenes = scene_extractor.extract_and_describe(
                    video_path, 
                    interval_seconds=30,  # Extract a frame every 30 seconds
                    max_frames=6,         # Maximum 6 frames to avoid long processing
                    task_id=self.request.id  # Pass the task ID for frame directory naming
                )
                
                # Generate AI prompts for each scene
                set_task_progress(self.request.id, 90, 'Generating AI prompts for scenes')
                from app.utils.prompt_generation import PromptGenerator
                prompt_generator = PromptGenerator()
                scenes_with_prompts = prompt_generator.generate_prompts_for_scenes(scenes)
                scenes_json = json.dumps(scenes_with_prompts)
            except Exception as e:
                print(f"Error extracting scenes: {str(e)}")
                traceback.print_exc()
                # Create a valid JSON structure even on error
                scenes_json = json.dumps([{
                    "index": 0,
                    "timestamp": 0,
                    "timestamp_formatted": "00:00",
                    "description": f"Error extracting scenes: {str(e)}"
                }])
            
            # Store the transcript, Spanish script, and scenes in Redis
            r = redis.Redis.from_url(REDIS_URL)
            task_key = f'celery-task-meta-{self.request.id}'
            
            # Check if the key exists and what type it is
            key_type = r.type(task_key).decode('utf-8')
            
            # If it's not a hash or doesn't exist, delete it and create a new hash
            if key_type != 'hash' and key_type != 'none':
                r.delete(task_key)
            
            # Store all data as a hash
            task_data = {
                'result': transcript,
                'spanish_script': spanish_script_json,
                'scenes': scenes_json,
                'status': 'success',
                'progress': '100',
                'status_msg': 'Completed'
            }
            r.hset(task_key, mapping=task_data)
            
            # Also use the helper function for consistency
            set_task_progress(self.request.id, 100, 'Completed', result=transcript)
            
            # Return transcript, Spanish script, and scenes
            return {
                "transcript": transcript, 
                "spanish_script": spanish_script,
                "scenes": scenes
            }
        except Exception as e:
            set_task_progress(self.request.id, 100, f'Failed: {str(e)}')
            raise

def transcribe_video(source_path_or_url, is_youtube=False, model_size='base'):
    with tempfile.TemporaryDirectory() as tmpdir:
        if is_youtube:
            video_path = download_youtube_video(source_path_or_url, tmpdir)
        else:
            video_path = source_path_or_url
        audio_path = os.path.join(tmpdir, 'audio.wav')
        extract_audio(video_path, audio_path)
        transcript = transcribe_audio(audio_path, model_size=model_size)
    return transcript
