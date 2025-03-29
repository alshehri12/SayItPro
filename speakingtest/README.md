# English Pronunciation Testing Web App

A Django web application that allows users to test their English pronunciation skills.

## Features

- Random English sentences for pronunciation practice
- Text-to-speech functionality to hear correct pronunciation
- Audio recording capability to capture user's speech
- AI-powered pronunciation scoring (simulated in the current version)
- Word-by-word pronunciation feedback
- Clean and modern user interface

## Requirements

- Python 3.7+
- Django 4.2+
- Web browser with microphone access

## Installation

1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies:
   ```
   pip install django
   ```
4. Run migrations:
   ```
   python manage.py migrate
   ```
5. Create a superuser (optional, for admin access):
   ```
   python manage.py createsuperuser
   ```
6. Run the development server:
   ```
   python manage.py runserver
   ```
7. Access the application at http://127.0.0.1:8000/

## Usage

1. Visit the home page to see a random sentence
2. Click "Listen" to hear the correct pronunciation
3. Click "Record" to start recording your pronunciation
4. Click "Stop" when you're done speaking
5. View your pronunciation score and word-by-word feedback
6. Click "Next Sentence" to practice with a new sentence

## Extending the App

To use real speech recognition and pronunciation evaluation:

1. Install a speech recognition library:
   ```
   pip install SpeechRecognition
   ```
2. Modify the `evaluate_pronunciation` view in `views.py` to use a real speech-to-text API
3. Implement a more sophisticated scoring algorithm based on phonetic comparison

## License

MIT
