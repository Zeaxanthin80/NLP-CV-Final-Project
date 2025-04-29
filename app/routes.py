
from flask import Blueprint, render_template, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
import os
import redis
import json
from app.utils.transcription import celery_transcribe
from celery.result import AsyncResult


bp = Blueprint('main', __name__)

ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'url'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/process', methods=['POST'])
def process_video():
    import traceback
    if 'video' not in request.files and 'youtube_url' not in request.form:
        return jsonify({'error': 'No video file or YouTube URL provided'}), 400

    if 'video' in request.files:
        file = request.files['video']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            task = celery_transcribe.apply_async(args=[filepath, False])
            return jsonify({'message': 'Video upload received. Processing...', 'task_id': task.id}), 202
        else:
            return jsonify({'error': 'Invalid file type'}), 400
    elif 'youtube_url' in request.form:
        youtube_url = request.form['youtube_url']
        task = celery_transcribe.apply_async(args=[youtube_url, True])
        return jsonify({'message': 'YouTube URL received. Processing...', 'task_id': task.id}), 202
    return jsonify({'error': 'Invalid file type'}), 400

@bp.route('/status/<task_id>')
def get_status(task_id):
    try:
        # Initialize response with basic info
        response = {
            'task_id': task_id,
            'status': 'pending',  # Default status
            'progress': 0,
            'status_msg': ''
        }
        
        # Try to get progress data directly from Redis
        try:
            r = redis.Redis.from_url('redis://localhost:6379/0')
            # First, check if the key exists and what type it is
            key = f'celery-task-meta-{task_id}'
            key_type = r.type(key).decode('utf-8') if r.exists(key) else 'none'
            
            if key_type == 'hash':
                # If it's a hash, get the progress data
                progress_data = r.hgetall(key)
                if progress_data:
                    # Get progress if it exists
                    if b'progress' in progress_data:
                        response['progress'] = int(progress_data.get(b'progress', 0))
                    
                    # Get status message if it exists
                    if b'status_msg' in progress_data:
                        response['status_msg'] = progress_data.get(b'status_msg', b'').decode('utf-8')
                    
                    # Get status if it exists
                    if b'status' in progress_data:
                        response['status'] = progress_data.get(b'status', b'pending').decode('utf-8')
                    
                    # Get result if it exists
                    if b'result' in progress_data:
                        try:
                            result_str = progress_data.get(b'result', b'').decode('utf-8')
                            if result_str:
                                response['transcript'] = result_str
                                # If we have a result and progress is 100%, set status to success
                                if response['progress'] == 100:
                                    response['status'] = 'success'
                        except Exception as e:
                            print(f"Error decoding result: {str(e)}")
                    
                    # Get structured transcript if it exists
                    if b'structured_transcript' in progress_data:
                        try:
                            structured_transcript_str = progress_data.get(b'structured_transcript', b'').decode('utf-8')
                            if structured_transcript_str:
                                import json
                                response['structured_transcript'] = json.loads(structured_transcript_str)
                        except Exception as e:
                            print(f"Error decoding structured transcript: {str(e)}")
                    
                    # Get Spanish script if it exists
                    if b'spanish_script' in progress_data:
                        try:
                            script_str = progress_data.get(b'spanish_script', b'').decode('utf-8')
                            if script_str:
                                import json
                                response['spanish_script'] = json.loads(script_str)
                        except Exception as e:
                            print(f"Error decoding Spanish script: {str(e)}")
                    
                    # Get scene descriptions if they exist
                    if b'scenes' in progress_data:
                        try:
                            scenes_str = progress_data.get(b'scenes', b'').decode('utf-8')
                            if scenes_str:
                                import json
                                response['scenes'] = json.loads(scenes_str)
                        except Exception as e:
                            print(f"Error decoding scene descriptions: {str(e)}")
                            import traceback
                            traceback.print_exc()
                    
                    # Get error if it exists
                    if b'error' in progress_data:
                        try:
                            error_str = progress_data.get(b'error', b'').decode('utf-8')
                            if error_str:
                                response['error'] = error_str
                                response['status'] = 'error'
                        except Exception as e:
                            print(f"Error decoding error: {str(e)}")
            elif key_type == 'string':
                # If it's a string, try to parse it as JSON
                try:
                    import json
                    result_str = r.get(key).decode('utf-8')
                    result_data = json.loads(result_str)
                    
                    # Update response with data from the JSON
                    if 'status' in result_data:
                        response['status'] = result_data['status']
                    if 'result' in result_data:
                        response['transcript'] = result_data['result']
                    if 'error' in result_data:
                        response['error'] = result_data['error']
                except Exception as e:
                    print(f"Error parsing Redis string: {str(e)}")
            else:
                # If the key doesn't exist or is of an unexpected type
                print(f"Redis key {key} is of type {key_type}, expected hash or string")
                
                # As a fallback, try to get basic info from AsyncResult
                try:
                    from celery.result import AsyncResult
                    task_result = AsyncResult(task_id)
                    response['status'] = task_result.status.lower()
                except Exception as e:
                    print(f"Fallback to AsyncResult failed: {str(e)}")
        except Exception as e:
            print(f"Error accessing Redis: {str(e)}")
            # Return a basic response even if Redis fails
            return jsonify(response)
        
        return jsonify(response)
    except Exception as e:
        import traceback
        print(f"Error in get_status: {str(e)}")
        print(traceback.format_exc())
        return jsonify({'error': str(e), 'status': 'error', 'task_id': task_id}), 500

@bp.route('/frames/<task_id>/<frame_index>')
def get_frame(task_id, frame_index):
    """
    Serve a frame image from a processed video.
    """
    try:
        # Get the frame data from Redis
        r = redis.Redis.from_url('redis://localhost:6379/0')
        key = f'celery-task-meta-{task_id}'
        
        print(f"DEBUG: Accessing frame for task {task_id}, frame {frame_index}")
        
        if not r.exists(key):
            print(f"DEBUG: Task {task_id} not found in Redis")
            return jsonify({'error': 'Task not found'}), 404
        
        # Get the scenes data
        scenes_str = r.hget(key, 'scenes')
        if not scenes_str:
            print(f"DEBUG: No scenes data for task {task_id}")
            return jsonify({'error': 'No scenes available for this task'}), 404
        
        # Parse the scenes data
        scenes = json.loads(scenes_str.decode('utf-8'))
        print(f"DEBUG: Found {len(scenes)} scenes for task {task_id}")
        
        frame_index = int(frame_index)
        if frame_index < 0 or frame_index >= len(scenes):
            print(f"DEBUG: Invalid frame index {frame_index}, max is {len(scenes)-1}")
            return jsonify({'error': 'Invalid frame index'}), 404
        
        # Get the frame path
        frame_path = scenes[frame_index].get('path')
        print(f"DEBUG: Frame path for index {frame_index}: {frame_path}")
        
        if not frame_path:
            print(f"DEBUG: No path found for frame {frame_index}")
            return jsonify({'error': 'Frame path not found'}), 404
            
        if not os.path.exists(frame_path):
            print(f"DEBUG: Frame file does not exist at path: {frame_path}")
            return jsonify({'error': 'Frame image file not found'}), 404
        
        # Serve the image file
        print(f"DEBUG: Serving frame image from {frame_path}")
        return send_file(frame_path, mimetype='image/jpeg')
    
    except Exception as e:
        import traceback
        print(f"DEBUG: Error in get_frame: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': f'Error retrieving frame: {str(e)}'}), 500
