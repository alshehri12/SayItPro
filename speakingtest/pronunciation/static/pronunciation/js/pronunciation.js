// Pronunciation Testing App JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const sentenceElement = document.getElementById('sentence');
    const btnSpeak = document.getElementById('btnSpeak');
    const btnRecord = document.getElementById('btnRecord');
    const btnStop = document.getElementById('btnStop');
    const btnNext = document.getElementById('btnNext');
    const recordingIndicator = document.getElementById('recordingIndicator');
    const resultsContainer = document.getElementById('resultsContainer');
    const overallScoreElement = document.getElementById('overallScore');
    const wordScoresContainer = document.getElementById('wordScores');
    const recordedAudio = document.getElementById('recordedAudio');
    
    // Variables for recording
    let mediaRecorder;
    let audioChunks = [];
    let recognition;
    let recognizedText = '';
    
    // Initialize speech recognition if available
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        // Create speech recognition object
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = true;  // Changed to true to capture more speech
        recognition.interimResults = true; // Show interim results
        recognition.maxAlternatives = 3; // Get multiple alternatives
        recognition.lang = 'en-US';
        
        // Set up recognition event handlers
        recognition.onresult = function(event) {
            let finalTranscript = '';
            let interimTranscript = '';
            
            // Process all results
            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const transcript = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += transcript;
                } else {
                    interimTranscript += transcript;
                }
            }
            
            if (finalTranscript) {
                recognizedText += ' ' + finalTranscript;
                recognizedText = recognizedText.trim();
                console.log('Updated recognized text:', recognizedText);
            }
            
            // Show interim results
            if (interimTranscript) {
                console.log('Interim transcript:', interimTranscript);
            }
        };
        
        recognition.onend = function() {
            console.log('Speech recognition service disconnected');
            // Try to restart if we're still recording
            if (mediaRecorder && mediaRecorder.state === 'recording') {
                try {
                    recognition.start();
                    console.log('Restarted speech recognition');
                } catch (e) {
                    console.error('Could not restart recognition:', e);
                }
            }
        };
        
        recognition.onerror = function(event) {
            console.error('Speech recognition error:', event.error);
        };
    } else {
        console.warn('Speech recognition not supported in this browser');
    }
    
    // Text-to-speech functionality
    btnSpeak.addEventListener('click', function() {
        const sentenceText = sentenceElement.textContent;
        const utterance = new SpeechSynthesisUtterance(sentenceText);
        utterance.lang = 'en-US';
        utterance.rate = 1;
        speechSynthesis.speak(utterance);
    });
    
    // Record button click
    btnRecord.addEventListener('click', function() {
        // Reset previous recording and recognition
        audioChunks = [];
        recognizedText = '';
        resultsContainer.style.display = 'none';
        
        // First get audio permission
        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                mediaRecorder = new MediaRecorder(stream);
                
                mediaRecorder.addEventListener('dataavailable', event => {
                    audioChunks.push(event.data);
                });
                
                mediaRecorder.addEventListener('stop', () => {
                    // Create audio blob and URL
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    recordedAudio.src = audioUrl;
                    
                    // Hide recording indicator
                    recordingIndicator.style.display = 'none';
                    
                    // Add a small delay to make sure recognition has time to finish
                    setTimeout(() => {
                        // Send to server for evaluation
                        console.log('Final recognized text:', recognizedText);
                        evaluatePronunciation(audioBlob, sentenceElement.textContent, recognizedText);
                    }, 500);
                });
                
                // Start recording
                mediaRecorder.start();
                
                // Start speech recognition after recording starts
                if (recognition) {
                    try {
                        setTimeout(() => {
                            recognition.start();
                            console.log('Speech recognition started');
                        }, 500);
                    } catch (e) {
                        console.error('Error starting recognition:', e);
                    }
                }
                
                // Update UI for recording state
                btnRecord.style.display = 'none';
                btnStop.style.display = 'inline-block';
                recordingIndicator.style.display = 'block';
            })
            .catch(err => {
                console.error('Error accessing microphone:', err);
                alert('Error accessing microphone. Please ensure you have given permission.');
            });
    });
    
    // Stop button click
    btnStop.addEventListener('click', function() {
        // Update UI immediately to show we're processing
        recordingIndicator.textContent = 'Processing...'; 
        recordingIndicator.style.animation = 'none';
        recordingIndicator.style.color = '#4285F4'; // Use primary color instead of danger color
        
        // Stop speech recognition first to get final results
        if (recognition) {
            try {
                recognition.stop();
                console.log('Speech recognition stopped');
                console.log('Final speech recognition result:', recognizedText);
            } catch (e) {
                console.log('Recognition already stopped');
            }
        }
        
        // Then stop media recorder after a small delay
        setTimeout(() => {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
                
                // Update UI
                btnRecord.style.display = 'inline-block';
                btnStop.style.display = 'none';
                
                // Stop all tracks to release the microphone
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        }, 800); // Longer delay to make sure recognition finishes
    });
    
    // Next sentence button click
    btnNext.addEventListener('click', function() {
        // Show loading state
        sentenceElement.innerHTML = '<span class="loading-text">Loading new sentence...</span>';
        
        // Get the active difficulty level
        let difficulty = 'all';
        const activeLevelTab = document.querySelector('.level-tab.active');
        if (activeLevelTab) {
            difficulty = activeLevelTab.textContent.toLowerCase();
        }
        
        // Fetch a new sentence with the selected difficulty
        fetch(`/api/random-sentence/?difficulty=${difficulty}`)
            .then(response => response.json())
            .then(data => {
                sentenceElement.textContent = data.sentence;
                resultsContainer.style.display = 'none';
                
                // Highlight the sentence briefly to show it changed
                sentenceElement.classList.add('sentence-highlight');
                setTimeout(() => {
                    sentenceElement.classList.remove('sentence-highlight');
                }, 500);
            })
            .catch(error => {
                console.error('Error fetching new sentence:', error);
                sentenceElement.textContent = 'Error loading sentence. Please try again.';
            });
    });
    
    // Handle difficulty level selection
    const levelTabs = document.querySelectorAll('.level-tab');
    levelTabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove active class from all tabs
            levelTabs.forEach(t => t.classList.remove('active'));
            // Add active class to clicked tab
            this.classList.add('active');
            
            // Get a new sentence with the selected difficulty
            btnNext.click();
        });
    });
    
    // Function to evaluate pronunciation
    function evaluatePronunciation(audioBlob, referenceText, transcribedText) {
        // Convert the audio blob to base64 to send in JSON
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        
        reader.onloadend = function() {
            const base64Audio = reader.result;
            console.log('Speech to be sent to server:', transcribedText);
            
            // Create a loading indicator
            const loadingIndicator = document.createElement('div');
            loadingIndicator.id = 'loadingIndicator';
            loadingIndicator.innerHTML = 'Processing your pronunciation...';
            loadingIndicator.style.fontSize = '1.2em';
            loadingIndicator.style.marginTop = '20px';
            loadingIndicator.style.textAlign = 'center';
            
            resultsContainer.innerHTML = '';
            resultsContainer.appendChild(loadingIndicator);
            resultsContainer.style.display = 'block';
            
            // Send both the audio data and any available transcribed text from Web Speech API
            fetch('/api/evaluate-pronunciation/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    speech: transcribedText || 'No speech detected', // Send the transcribed text
                    audio_data: base64Audio,  // Send the complete audio data
                    reference: referenceText
                })
            })
            .then(response => response.json())
            .then(data => {
                // Remove loading indicator if it exists
                const loadingIndicator = document.getElementById('loadingIndicator');
                if (loadingIndicator) {
                    loadingIndicator.remove();
                }
                
                // Display results
                overallScoreElement.textContent = data.overall_score;
                
                // Make sure the results container is visible
                console.log('Showing results container');
                resultsContainer.style.display = 'block';
                
                // Show recognized text
                const recognizedTextElement = document.createElement('div');
                recognizedTextElement.className = 'recognized-text';
                recognizedTextElement.innerHTML = `<strong>Your speech:</strong> ${data.recognized_text || 'No speech detected'}`;
                recognizedTextElement.style.margin = '10px 0';
                recognizedTextElement.style.padding = '10px';
                recognizedTextElement.style.backgroundColor = '#f8f9fa';
                recognizedTextElement.style.borderRadius = '5px';
                
                // Clear previous word scores
                wordScoresContainer.innerHTML = '';
                wordScoresContainer.appendChild(recognizedTextElement);
                
                // Add word scores with phoneme-level analysis
                Object.entries(data.word_scores).forEach(([word, score]) => {
                    const wordElement = document.createElement('div');
                    wordElement.className = 'word-score-item';
                    
                    let scoreClass = '';
                    if (score >= 80) {
                        scoreClass = 'score-good';
                    } else if (score >= 60) {
                        scoreClass = 'score-medium';
                    } else {
                        scoreClass = 'score-poor';
                    }
                    
                    // Check if we have phoneme analysis for this word
                    let wordContent = '';
                    if (data.phoneme_analysis && data.phoneme_analysis[word]) {
                        const analysis = data.phoneme_analysis[word];
                        const refPhonemes = analysis.reference_phonemes;
                        const problemPhonemes = analysis.problem_phonemes;
                        
                        // First try to highlight at the phoneme level if we have the data
                        if (refPhonemes && refPhonemes.length > 0) {
                            // Create a phoneme-level display with highlighting
                            const highlightedPhonemes = [];
                            
                            for (let i = 0; i < refPhonemes.length; i++) {
                                if (problemPhonemes.includes(i)) {
                                    // Problem phoneme - mark in red
                                    highlightedPhonemes.push('<span class="problem-phoneme" title="Mispronounced">' + refPhonemes[i] + '</span>');
                                } else {
                                    // Correctly pronounced phoneme
                                    highlightedPhonemes.push('<span class="correct-phoneme">' + refPhonemes[i] + '</span>');
                                }
                            }
                            
                            // Build IPA notation display
                            const phoneticDisplay = '<div class="phonetic-display">/' + highlightedPhonemes.join('') + '/</div>';
                            
                            // Now highlight the actual word text
                            let highlightedWord = word;
                            if (problemPhonemes.length > 0) {
                                // Create a simple highlighting for the Roman alphabet display
                                const letters = word.split('');
                                const letterCount = letters.length;
                                const problemIndices = [];
                                
                                // Roughly map phoneme problems to letter positions
                                problemPhonemes.forEach(phIdx => {
                                    // Map the phoneme index to a letter index (simplified mapping)
                                    const letterIdx = Math.floor((phIdx / refPhonemes.length) * letterCount);
                                    if (letterIdx >= 0 && letterIdx < letterCount) {
                                        problemIndices.push(letterIdx);
                                    }
                                });
                                
                                // Highlight the letters
                                const highlightedLetters = letters.map((letter, idx) => {
                                    if (problemIndices.includes(idx)) {
                                        return '<span class="problem-letter">' + letter + '</span>';
                                    }
                                    return letter;
                                });
                                
                                highlightedWord = highlightedLetters.join('');
                            }
                            
                            wordContent = `
                                <div class="word-text">${highlightedWord}</div>
                                ${phoneticDisplay}
                                <div class="word-score ${scoreClass}">${score}</div>
                                <div class="phoneme-tip">Highlighted sounds need more practice</div>
                            `;
                        } else {
                            // Fallback to regular display
                            wordContent = `
                                <div class="word-text">${word}</div>
                                <div class="word-score ${scoreClass}">${score}</div>
                            `;
                        }
                    } else {
                        // No phoneme analysis available, show regular display
                        wordContent = `
                            <div class="word-text">${word}</div>
                            <div class="word-score ${scoreClass}">${score}</div>
                        `;
                    }
                    
                    wordElement.innerHTML = wordContent;
                    
                    wordScoresContainer.appendChild(wordElement);
                });
                
                // Make sure audio element is updated with controls
                if (recordedAudio.src) {
                    recordedAudio.controls = true;
                }
                
                // Force layout update by adding a small delay
                setTimeout(() => {
                    // Show results
                    resultsContainer.style.display = 'block';
                    // Scroll to results
                    resultsContainer.scrollIntoView({ behavior: 'smooth' });
                }, 100);
            })
            .catch(error => {
                console.error('Error evaluating pronunciation:', error);
                
                // Remove loading indicator if it exists
                const loadingIndicator = document.getElementById('loadingIndicator');
                if (loadingIndicator) {
                    loadingIndicator.remove();
                }
                
                // Display error in the results container
                resultsContainer.style.display = 'block';
                resultsContainer.innerHTML = `
                    <div class="error-message" style="color: red; text-align: center; padding: 20px;">
                        <h4>Error Processing Speech</h4>
                        <p>There was a problem processing your speech. Please try again.</p>
                    </div>
                `;
                
                // Try to get more detailed error info if possible
                if (error.text) {
                    error.text().then(errorText => {
                        console.error('Error details:', errorText);
                    }).catch(() => {
                        console.error('Could not get detailed error text');
                    });
                }
            });
        };
    }
    
    // Function to get CSRF token from cookies
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
});
