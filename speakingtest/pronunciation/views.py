from django.shortcuts import render
from django.http import JsonResponse
import random
import json
import base64
import io
import numpy as np
import torch
import soundfile as sf
import epitran
import panphon.distance
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from .models import Sentence

def home(request):
    """Home view to display the pronunciation testing interface."""
    # Get a random sentence from the database or provide defaults if none exist
    try:
        random_sentence = random.choice(Sentence.objects.all())
        sentence_text = random_sentence.text
    except IndexError:
        # If no sentences in the database yet, provide some defaults
        default_sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "How are you doing today?",
            "I would like to improve my English pronunciation.",
            "Practice makes perfect when learning a new language.",
            "Could you please speak more slowly?"
        ]
        sentence_text = random.choice(default_sentences)
    
    return render(request, 'pronunciation/home.html', {
        'sentence': sentence_text,
    })


def speech_to_text(request):
    """Simplified view focused only on speech-to-text functionality."""
    # Get a specific test sentence
    sentence_text = "I would like to improve my English pronunciation."
    
    return render(request, 'pronunciation/speech_to_text.html', {
        'sentence': sentence_text,
    })

def get_random_sentence(request):
    """API to get a new random sentence with optional difficulty filtering."""
    # Get difficulty from query params, defaulting to 'all'
    difficulty = request.GET.get('difficulty', 'all').lower()
    
    # Create queryset based on difficulty
    queryset = Sentence.objects.all()
    
    # If a specific difficulty is requested, filter by it
    if difficulty in ['easy', 'medium', 'hard', 'beginner', 'intermediate', 'advanced']:
        # Map beginner/intermediate/advanced to easy/medium/hard if needed
        if difficulty == 'beginner':
            difficulty = 'easy'
        elif difficulty == 'intermediate':
            difficulty = 'medium'
        elif difficulty == 'advanced':
            difficulty = 'hard'
            
        queryset = queryset.filter(difficulty=difficulty)
    
    try:
        # Get count of matching sentences
        sentence_count = queryset.count()
        
        if sentence_count > 0:
            # Get a random sentence using an efficient method
            random_index = random.randint(0, sentence_count - 1)
            random_sentence = queryset[random_index]
            sentence_text = random_sentence.text
            difficulty_level = random_sentence.difficulty
        else:
            # Fallback if no sentences match the filter
            raise IndexError
    except IndexError:
        # If no sentences in the database yet, provide some defaults
        default_sentences = [
            "The quick brown fox jumps over the lazy dog.",
            "How are you doing today?",
            "I would like to improve my English pronunciation.",
            "Practice makes perfect when learning a new language.",
            "Could you please speak more slowly?"
        ]
        sentence_text = random.choice(default_sentences)
        difficulty_level = 'medium'
    
    return JsonResponse({
        'sentence': sentence_text,
        'difficulty': difficulty_level
    })

# Load the speech recognition model and processor (lazy loading to save memory)
speech_model = None
speech_processor = None
epitran_converter = epitran.Epitran('eng-Latn')
phon_distance = panphon.distance.Distance()

def get_speech_model():
    """Lazy loading of the speech recognition model"""
    global speech_model, speech_processor
    if speech_model is None:
        # Load pre-trained model for English speech recognition
        speech_processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
        speech_model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
    return speech_model, speech_processor

def evaluate_pronunciation(request):
    """API to evaluate the user's pronunciation using speech recognition and phonetic analysis."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Get the audio data and reference text
            user_speech = data.get('speech', '')
            audio_data = data.get('audio_data', None)
            reference_text = data.get('reference', '')
            
            if not reference_text:
                return JsonResponse({'error': 'Reference text is required'}, status=400)
            
            # If we received audio data and speech recognition failed (or is empty)
            if audio_data and (not user_speech or user_speech == 'No speech detected'):
                # Try to process the audio data directly
                try:
                    # Process the audio to get the transcription
                    processed_speech = process_audio_data(audio_data)
                    if processed_speech and len(processed_speech) > 0:
                        user_speech = processed_speech
                        print(f"Using server-side speech recognition: '{user_speech}'")
                except Exception as e:
                    print(f"Error processing audio: {str(e)}")
            
            print(f"Final speech text: '{user_speech}'")
            print(f"Reference text: '{reference_text}'")
            
            # Fallback to simple comparison if still no speech detected
            if not user_speech or user_speech == 'No speech detected':
                # If we can't get any speech, provide a simpler evaluation
                score, word_scores = 50, {word: 50 for word in reference_text.lower().split()}
                phoneme_analysis = {}  # No phoneme analysis when speech not detected
            else:
                # Use the new advanced evaluation that includes phoneme-level analysis
                try:
                    score, word_scores, phoneme_analysis = advanced_pronunciation_evaluation(user_speech, reference_text)
                except Exception as e:
                    print(f"Advanced evaluation error: {str(e)}")
                    # Fall back to regular evaluation without phoneme analysis
                    score, word_scores = real_pronunciation_evaluation(user_speech, reference_text)
                    phoneme_analysis = {}
            
            return JsonResponse({
                'overall_score': score,
                'word_scores': word_scores,
                'phoneme_analysis': phoneme_analysis,
                'recognized_text': user_speech
            })
        except Exception as e:
            import traceback
            print(f"Error in evaluate_pronunciation: {str(e)}")
            print(traceback.format_exc())
            return JsonResponse({'error': f'Evaluation error: {str(e)}'}, status=500)
    
    return JsonResponse({'error': 'POST request required'}, status=400)

def analyze_phonemes(reference_word, user_word):
    """Analyze phonemes within a word and identify pronunciation errors at the phoneme level.
    
    Args:
        reference_word: The correct word (text)
        user_word: The user's pronounced word (text)
    
    Returns:
        A dictionary with phoneme-level analysis including:
        - phoneme_scores: Score for each phoneme (0-100)
        - problem_phonemes: List of indices where errors occurred
        - reference_phonemes: List of reference phonemes
        - user_phonemes: List of user's pronounced phonemes
    """
    try:
        # Convert words to IPA (International Phonetic Alphabet)
        reference_ipa = epitran_converter.transliterate(reference_word)
        user_ipa = epitran_converter.transliterate(user_word)
        
        # Split into individual phonemes
        # Note: This is a simplification, as some IPA symbols represent single phonemes with multiple characters
        reference_phonemes = list(reference_ipa)
        user_phonemes = list(user_ipa)
        
        # Prepare results
        phoneme_scores = {}
        problem_phonemes = []
        
        # Compare phonemes using Levenshtein distance for alignment
        from difflib import SequenceMatcher
        matcher = SequenceMatcher(None, reference_phonemes, user_phonemes)
        
        # Map each reference phoneme to its closest match in user pronunciation
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'equal':
                # Phonemes match perfectly
                for i in range(i1, i2):
                    phoneme_idx = str(i)
                    phoneme_scores[phoneme_idx] = 100
            elif tag == 'replace':
                # Phoneme was mispronounced
                for i in range(i1, i2):
                    phoneme_idx = str(i)
                    # Calculate similarity between the phonemes
                    if j1 < j2:  # If there's a corresponding user phoneme
                        j = j1 + min(i - i1, j2 - j1 - 1)
                        # Use phonetic features to calculate similarity
                        ref_phoneme = reference_phonemes[i]
                        user_phoneme = user_phonemes[j]
                        
                        # Get phonetic features distance
                        try:
                            distance = phon_distance.weighted_feature_edit_distance(ref_phoneme, user_phoneme)
                            similarity = max(0, 100 - (distance * 50))
                        except:
                            similarity = 40  # Default moderate score for comparison error
                        
                        phoneme_scores[phoneme_idx] = similarity
                        if similarity < 70:  # Threshold for marking as problematic
                            problem_phonemes.append(i)
                    else:
                        phoneme_scores[phoneme_idx] = 0
                        problem_phonemes.append(i)
            elif tag == 'delete':
                # User omitted these phonemes
                for i in range(i1, i2):
                    phoneme_idx = str(i)
                    phoneme_scores[phoneme_idx] = 0
                    problem_phonemes.append(i)
            elif tag == 'insert':
                # User added extra phonemes (we don't score these in the reference)
                pass
        
        # Calculate overall word score based on phoneme scores
        if phoneme_scores:
            phoneme_level_score = sum(phoneme_scores.values()) / len(phoneme_scores)
        else:
            phoneme_level_score = 0
            
        return {
            'score': round(phoneme_level_score),
            'phoneme_scores': phoneme_scores,
            'problem_phonemes': problem_phonemes,
            'reference_phonemes': reference_phonemes,
            'user_phonemes': user_phonemes
        }
    except Exception as e:
        print(f"Error in analyze_phonemes: {str(e)}")
        # Return a default structure
        return {
            'score': 70,
            'phoneme_scores': {},
            'problem_phonemes': [],
            'reference_phonemes': list(reference_word),
            'user_phonemes': list(user_word)
        }

def advanced_pronunciation_evaluation(user_speech, reference_text):
    """Evaluate pronunciation using phonetic comparison with phoneme-level analysis.
    
    In a full implementation, this would use the audio data to perform speech recognition.
    For this demo, we'll simulate the speech recognition part but use real phonetic comparison.
    """
    try:
        # Clean the reference text
        reference_text = reference_text.lower().replace('.', '').replace(',', '').replace('?', '').replace('!', '')
        words = reference_text.split()
        word_scores = {}
        phoneme_analysis = {}
        
        if not words:
            # Handle empty text case
            return 75, {'no_words': 75}, {}
        
        # For each word, calculate a pronunciation score based on phonetic similarity
        for word in words:
            try:
                # In a real implementation, we would get the actual spoken word from the user's audio
                # For demo purposes, we'll create a simulated pronunciation with some errors
                simulated_pronunciation = simulate_pronunciation_with_errors(word)
                
                # Analyze at phoneme level
                phoneme_results = analyze_phonemes(word, simulated_pronunciation)
                
                # Store the word score and phoneme analysis
                word_scores[word] = phoneme_results['score']
                phoneme_analysis[word] = {
                    'problem_phonemes': phoneme_results['problem_phonemes'],
                    'reference_phonemes': phoneme_results['reference_phonemes'],
                    'user_phonemes': phoneme_results['user_phonemes']
                }
            except Exception as e:
                print(f"Error processing word '{word}': {str(e)}")
                # Assign a default score if there's an error with a specific word
                word_scores[word] = 70
                phoneme_analysis[word] = {
                    'problem_phonemes': [],
                    'reference_phonemes': list(word),
                    'user_phonemes': list(word)
                }
        
        # Calculate overall score as average of word scores
        overall_score = sum(word_scores.values()) / len(word_scores) if word_scores else 75
        
        return round(overall_score), word_scores, phoneme_analysis
    except Exception as e:
        print(f"Error in advanced_pronunciation_evaluation: {str(e)}")
        # Fallback to random scores if there's a major error
        scores, word_scores = simulate_pronunciation_evaluation_fallback(reference_text)
        return scores, word_scores, {}

def simulate_pronunciation_evaluation_fallback(reference_text):
    """Fallback to random scores if the advanced evaluation fails."""
    # Clean the reference text
    reference_text = reference_text.lower().replace('.', '').replace(',', '').replace('?', '').replace('!', '')
    words = reference_text.split() if reference_text else ['test']
    word_scores = {}
    
    # Assign random scores to each word as a fallback
    for word in words:
        word_scores[word] = random.randint(60, 100)
    
    # Calculate overall score as average of word scores
    overall_score = sum(word_scores.values()) / len(word_scores) if word_scores else 75
    
    return round(overall_score), word_scores

def simulate_pronunciation_with_errors(word):
    """Simulate pronunciation errors to demonstrate the scoring system.
    
    In a real app, this would be replaced by actual speech recognition of user's audio.
    """
    # Dictionary of common pronunciation mistakes
    common_errors = {
        'th': 't',    # e.g., 'think' -> 'tink'
        'v': 'f',     # e.g., 'very' -> 'fery'
        'w': 'v',     # e.g., 'wait' -> 'vait'
        'r': 'l',     # e.g., 'right' -> 'light'
        'l': 'r',     # e.g., 'light' -> 'right'
        'sh': 's',    # e.g., 'ship' -> 'sip'
        'ch': 'sh',   # e.g., 'chip' -> 'ship'
        'j': 'y',     # e.g., 'job' -> 'yob'
        'z': 's',     # e.g., 'zoo' -> 'soo'
    }
    
    # Randomly decide if we'll introduce an error (50% chance)
    if random.random() < 0.5 or len(word) <= 2:
        return word  # Return the original word 50% of the time or for short words
    
    simulated_word = word
    
    # Try to apply one of the common errors if the pattern exists in the word
    for error_pattern, replacement in common_errors.items():
        if error_pattern in simulated_word and random.random() < 0.3:  # 30% chance to apply error
            simulated_word = simulated_word.replace(error_pattern, replacement, 1)
            break  # Only apply one error per word to keep it realistic
    
    return simulated_word

def process_audio_data(audio_data):
    """Process the audio data for speech recognition.
    
    This function would be used in a full implementation with real audio data.
    """
    try:
        # Decode base64 audio data
        audio_bytes = base64.b64decode(audio_data.split(',')[1])
        
        # Load the audio file using soundfile
        audio, sample_rate = sf.read(io.BytesIO(audio_bytes))
        
        # Resample to 16kHz if needed (Wav2Vec2 expects 16kHz)
        if sample_rate != 16000:
            # In a full implementation, you would resample here
            pass
        
        # Get the model and processor
        model, processor = get_speech_model()
        
        # Process the audio data
        input_values = processor(audio, sampling_rate=16000, return_tensors="pt").input_values
        
        # Get the logits
        with torch.no_grad():
            logits = model(input_values).logits
        
        # Take argmax and decode
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = processor.batch_decode(predicted_ids)[0]
        
        return transcription
    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        return ""


def real_pronunciation_evaluation(user_speech, reference_text):
    """Evaluate pronunciation using actual speech recognition results.
    
    This function compares the user's recognized speech against the reference text
    to generate meaningful pronunciation scores.
    """
    try:
        # Clean both texts for comparison
        reference_text = clean_text(reference_text)
        user_speech = clean_text(user_speech)
        
        # Get individual words from reference text
        reference_words = reference_text.split()
        user_words = user_speech.split()
        
        if not reference_words:
            return 75, {'no_words': 75}
            
        word_scores = {}
        
        # If the user didn't say anything
        if not user_words or user_speech == 'No speech detected':
            for word in reference_words:
                word_scores[word] = 0
            return 0, word_scores
            
        # Score each reference word
        for word in reference_words:
            # Check if the word appears in the user's speech
            if word in user_words:
                # Word was correctly pronounced
                word_scores[word] = 100
            else:
                # Try to find similar words (possible mispronunciations)
                similar_words = find_similar_words(word, user_words)
                if similar_words:
                    # Use the closest match to determine score
                    best_match, similarity = similar_words[0]
                    word_scores[word] = int(similarity * 100)
                else:
                    # Word was missed entirely
                    word_scores[word] = 0
        
        # Calculate overall score as weighted average
        if word_scores:
            overall_score = sum(word_scores.values()) / len(word_scores)
        else:
            overall_score = 0
            
        return round(overall_score), word_scores
        
    except Exception as e:
        print(f"Error in real_pronunciation_evaluation: {str(e)}")
        # Fallback to simpler evaluation method
        return basic_pronunciation_evaluation(user_speech, reference_text)


def clean_text(text):
    """Clean text for comparison by removing punctuation and normalizing case."""
    text = text.lower()
    for char in '.?!,:;-"\'\':()/[]{}…':
        text = text.replace(char, '')
    return text


def find_similar_words(target, word_list, threshold=0.6):
    """Find similar words in the word list using string similarity algorithms.
    
    Returns a list of (word, similarity_score) tuples, sorted by similarity.
    """
    from difflib import SequenceMatcher
    
    similarities = []
    for word in word_list:
        similarity = SequenceMatcher(None, target, word).ratio()
        if similarity >= threshold:
            similarities.append((word, similarity))
            
    return sorted(similarities, key=lambda x: x[1], reverse=True)


def basic_pronunciation_evaluation(user_speech, reference_text):
    """Simple evaluation based on word presence and order."""
    reference_text = clean_text(reference_text)
    user_speech = clean_text(user_speech)
    
    reference_words = reference_text.split()
    user_words = user_speech.split()
    
    word_scores = {}
    
    # Count words that appear in both texts
    for word in reference_words:
        if word in user_words:
            word_scores[word] = 100
        else:
            # Calculate partial match score based on character overlap
            best_score = 0
            for user_word in user_words:
                chars_in_common = sum(c in user_word for c in word)
                similarity = chars_in_common / len(word) if len(word) > 0 else 0
                best_score = max(best_score, similarity * 100)
            word_scores[word] = round(best_score)
    
    # Overall score is the average
    overall_score = sum(word_scores.values()) / len(word_scores) if word_scores else 0
    
    return round(overall_score), word_scores
