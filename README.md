# Video Content Adaptation System

This project combines Natural Language Processing (NLP) and Computer Vision (CV) technologies to create an application that can:
1. Transcribe YouTube videos in any language
2. Create contextually similar video scripts in Spanish
3. Extract scene descriptions using Computer Vision
4. Generate AI image/video prompts for similar scene creation

## Setup

1. Create a virtual environment and activate it:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in your API keys:
```bash
cp .env.example .env
# Edit .env with your API keys
```

## Project Structure

```
.
├── app/
│   ├── static/      # Static files (CSS, JS, images)
│   ├── templates/   # HTML templates
│   └── utils/       # Utility functions
├── uploads/         # Temporary storage for uploaded files
├── requirements.txt # Project dependencies
├── .env.example    # Example environment variables
└── README.md       # This file
```

## Features

1. **Video Transcription**
   - Supports multiple languages
   - Uses OpenAI Whisper for accurate transcription

2. **Spanish Script Generation**
   - Contextual adaptation rather than direct translation
   - Maintains original message and tone

3. **Scene Analysis**
   - Computer Vision-based scene description
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
