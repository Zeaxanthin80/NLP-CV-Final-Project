# Video Content Adaptation System

![Project Banner](https://img.shields.io/badge/NLP%20%2B%20CV-Final%20Project-blue)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)
![Celery](https://img.shields.io/badge/Celery-5.0%2B-orange)

This project combines Natural Language Processing (NLP) and Computer Vision (CV) technologies to create a comprehensive video content adaptation system that can:

1. **Transcribe YouTube videos** in any language with high accuracy
2. **Create contextually similar video scripts in Spanish** with proper structure
3. **Extract and analyze scenes** using Computer Vision techniques
4. **Generate AI image/video prompts** for recreating similar visual content

## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/Zeaxanthin80/NLP-CV-Final-Project.git
cd NLP-CV-Final-Project
```

2. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
# Edit .env with your API keys
```

5. Download NLTK data:
```bash
python download_nltk_data.py
```

## Running the Application

1. Start Redis server (required for Celery):
```bash
redis-server
```

2. Start Celery worker in a separate terminal:
```bash
celery -A celery_worker.celery worker --loglevel=info
```

3. Start the Flask application:
```bash
python main.py
```

4. Open your browser and navigate to http://127.0.0.1:5000

## Technology Stack

### NLP Technologies
- **OpenAI Whisper**: State-of-the-art speech recognition model for transcription
- **MarianMT**: Neural machine translation model for Spanish script generation
- **NLTK**: Natural Language Toolkit for text processing and tokenization
- **Transformers**: Hugging Face library for NLP tasks and models

### CV Technologies
- **OpenCV**: Computer vision library for video and frame processing
- **BLIP**: Bootstrapping Language-Image Pre-training for image captioning
- **PyTorch**: Deep learning framework for running CV models
- **PIL**: Python Imaging Library for image manipulation

### Web Technologies
- **Flask**: Web framework for the application backend
- **Celery**: Distributed task queue for asynchronous processing
- **Redis**: Message broker and result backend for Celery
- **Tailwind CSS**: Utility-first CSS framework for the frontend

## Project Structure

```
.
├── app/
│   ├── static/       # Static files (CSS, JS, images)
│   │   └── frames/   # Extracted video frames
│   ├── templates/    # HTML templates
│   └── utils/        # Utility functions
│       ├── transcription.py     # Video transcription
│       ├── script_generation.py # Spanish script generation
│       ├── scene_extraction.py  # CV scene extraction
│       └── prompt_generation.py # AI prompt generation
├── uploads/          # Temporary storage for uploaded files
├── requirements.txt  # Project dependencies
├── main.py           # Application entry point
├── celery_worker.py  # Celery worker configuration
├── .env.example      # Example environment variables
└── README.md         # This file
```

## Features

1. **Video Transcription**
   - Supports multiple languages through OpenAI Whisper
   - Processes both YouTube URLs and uploaded video files
   - Real-time progress updates during processing
   - Asynchronous processing with Celery and Redis

2. **Spanish Script Generation**
   - Contextual adaptation rather than direct translation
   - Maintains original message and tone
   - Structures content into proper video script format:
     - Hook (0-15s)
     - Intro/Branding (15-30s)
     - Main Content
     - Call to Action
     - Outro

3. **Scene Extraction and Analysis**
   - Extracts frames from videos at regular intervals
   - Generates scene descriptions using BLIP image captioning model
   - Displays extracted frames with timestamps and descriptions
   - Preserves frames in static storage for future reference

4. **AI Prompt Generation**
   - Creates specialized prompts for AI image generators (DALL-E, Midjourney, etc.)
   - Generates video-specific prompts with motion elements
   - Enhances descriptions with lighting, camera, and style details
   - Adapts to different scene types (interviews, presentations, outdoor scenes, etc.)

## Usage

1. **Transcribe a YouTube Video**:
   - Enter a YouTube URL in the input field
   - Click "Process Video"
   - Wait for the processing to complete
   - View the transcript, Spanish script, scene descriptions, and AI prompts

2. **Process an Uploaded Video**:
   - Click on "File Upload"
   - Select a video file from your computer
   - Click "Process Video"
   - View the results as above

## Future Enhancements

- Integration with AI image generation APIs (DALL-E, Midjourney)
- Support for more languages in script generation
- Enhanced scene detection with object recognition
- User accounts and saved projects
- Video editing suggestions based on transcript analysis

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- OpenAI for the Whisper model
- Hugging Face for the Transformers library
- The BLIP team for their image captioning model
- Flask, Celery, and Redis communities for their excellent documentation
   - Key object and action detection

4. **AI Prompt Generation**
   - Creates prompts for image/video generation
   - Maintains visual consistency with original content

## Development

This project follows the standard Flask application structure. To run the development server:

```bash
flask run
```

## License

[Your chosen license]
