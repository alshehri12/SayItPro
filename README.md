# SayItPro - English Pronunciation Testing App

SayItPro is a web application that helps users improve their English pronunciation by providing real-time feedback on their speech.

## Features

- **Speech Recognition**: Uses Web Speech API to convert speech to text
- **Real-time Evaluation**: Compares user's pronunciation against reference sentences
- **Word-by-word Analysis**: Shows which words were pronounced correctly, partially correct, or missing
- **Scoring System**: Provides an overall pronunciation score
- **Audio Recording**: Records audio for playback and review
- **Modern UI**: Clean, responsive interface inspired by language learning apps

## Technologies Used

- **Frontend**: HTML, CSS, JavaScript
- **Backend**: Django
- **Speech Recognition**: Web Speech API
- **Audio Recording**: MediaRecorder API
- **Styling**: Bootstrap with custom CSS

## Getting Started

1. Clone the repository:
```
git clone https://github.com/alshehri12/SayItPro.git
cd SayItPro
```

2. Create a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Run the server:
```
cd speakingtest
python manage.py runserver
```

5. Visit `http://127.0.0.1:8000/` in your browser (Chrome or Edge recommended for full functionality)

## Browser Compatibility

The application works best with browsers that support the Web Speech API:
- Google Chrome
- Microsoft Edge

## License

This project is licensed under the MIT License - see the LICENSE file for details.
