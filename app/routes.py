
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename
import os
import redis
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
                    
                    # Get Spanish script if it exists
                    if b'spanish_script' in progress_data:
                        try:
                            script_str = progress_data.get(b'spanish_script', b'').decode('utf-8')
                            if script_str:
                                import json
                                response['spanish_script'] = json.loads(script_str)
                        except Exception as e:
                            print(f"Error decoding Spanish script: {str(e)}")
                    
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
