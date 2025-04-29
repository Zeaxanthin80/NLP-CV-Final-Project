import os
import tempfile
import subprocess
import json
from pytube import YouTube
import whisper

# Download YouTube video and return the path to the downloaded file

def download_youtube_video(youtube_url, download_dir):
    """
    Downloads the best audio from a YouTube URL using yt-dlp and returns the path to the downloaded file.
    """
    import shutil
    yt_dlp_path = shutil.which("yt-dlp")
    if not yt_dlp_path:
        raise RuntimeError("yt-dlp is not installed or not found in PATH.")
    output_path = os.path.join(download_dir, '%(title)s.%(ext)s')
    command = [
        yt_dlp_path,
        '-f', 'bestaudio',
        '--extract-audio',
        '--audio-format', 'wav',
        '--audio-quality', '0',
        '-o', output_path,
        youtube_url
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {result.stderr.decode('utf-8')}")
    # Find the downloaded .wav file in download_dir
    for fname in os.listdir(download_dir):
        if fname.endswith('.wav'):
            return os.path.join(download_dir, fname)
    raise RuntimeError("Audio file not found after yt-dlp download.")

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
                set_task_progress(self.request.id, 10, 'Downloading YouTube audio')
                video_path = download_youtube_video(source_path_or_url, tmpdir)
            else:
                set_task_progress(self.request.id, 10, 'Processing uploaded video')
                video_path = source_path_or_url
            audio_path = os.path.join(tmpdir, 'audio.wav')
            set_task_progress(self.request.id, 40, 'Extracting audio')
            extract_audio(video_path, audio_path)
            set_task_progress(self.request.id, 60, 'Transcribing audio')
            transcript = transcribe_audio(audio_path, model_size=model_size)
            
            # Generate Spanish script
            set_task_progress(self.request.id, 80, 'Generating Spanish script')
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
            
            # Store the transcript and Spanish script in Redis
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
                'status': 'success',
                'progress': '100',
                'status_msg': 'Completed'
            }
            r.hset(task_key, mapping=task_data)
            
            # Also use the helper function for consistency
            set_task_progress(self.request.id, 100, 'Completed', result=transcript)
            
            # Return both transcript and Spanish script
            return {"transcript": transcript, "spanish_script": spanish_script}
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
