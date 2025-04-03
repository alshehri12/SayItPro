from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Sum
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
import base64
import os
import tempfile
from datetime import timedelta
import speech_recognition as sr
from pronunciation.views import advanced_pronunciation_evaluation, analyze_phonemes
from .models import (
    ReadingLevel, ReadingMaterial, ReadingSession, 
    ReadingAnalysis, ReadingProgress, Badge, StudentBadge
)

# Helper functions
def calculate_reading_speed(text, duration_seconds):
    """Calculate words per minute"""
    if not duration_seconds or duration_seconds <= 0:
        return 0
    
    word_count = len(text.split())
    minutes = duration_seconds / 60
    return word_count / minutes if minutes > 0 else 0

def save_audio_file(base64_audio, session_id):
    """Save base64 encoded audio to a file"""
    # Strip the header from the base64 string if present
    if ',' in base64_audio:
        header, base64_audio = base64_audio.split(',', 1)
    
    # Decode base64 string to binary
    audio_data = base64.b64decode(base64_audio)
    
    # Create directory if it doesn't exist
    upload_dir = os.path.join('media', 'reading_recordings')
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate filename based on session ID
    filename = f"session_{session_id}.wav"
    file_path = os.path.join(upload_dir, filename)
    
    # Write binary data to file
    with open(file_path, 'wb') as f:
        f.write(audio_data)
    
    return file_path

def speech_to_text(audio_file_path):
    """Convert speech to text using speech recognition"""
    recognizer = sr.Recognizer()
    
    with sr.AudioFile(audio_file_path) as source:
        audio_data = recognizer.record(source)
        
    try:
        text = recognizer.recognize_google(audio_data, language='en-US')
        return text
    except sr.UnknownValueError:
        return ""
    except sr.RequestError:
        return ""

def analyze_reading_accuracy(reference_text, spoken_text):
    """Analyze reading accuracy using our existing pronunciation evaluation"""
    # Use the same function from pronunciation app
    result = advanced_pronunciation_evaluation(spoken_text, reference_text)
    
    # Extract accuracy percentage
    accuracy = result.get('score', 0)
    
    # Get word-level details
    word_results = result.get('word_scores', {})
    
    # Extract mispronounced words with phoneme analysis
    mispronounced_words = {}
    for word, details in word_results.items():
        if details.get('score', 0) < 70:  # Consider a word mispronounced if score < 70
            reference_word = word
            user_word = details.get('user_word', '')
            if user_word and reference_word:
                phoneme_analysis = analyze_phonemes(reference_word, user_word)
                mispronounced_words[word] = {
                    'score': details.get('score', 0),
                    'user_word': user_word,
                    'phoneme_analysis': phoneme_analysis
                }
    
    return {
        'accuracy': accuracy,
        'mispronounced_words': mispronounced_words
    }

# Fluency assessment could include analyzing pauses, repetitions, etc.
def analyze_fluency(spoken_text, duration_seconds, reference_text):
    """Basic fluency analysis based on speaking rate and comparison to reference"""
    # Calculate words per minute
    wpm = calculate_reading_speed(spoken_text, duration_seconds)
    
    # Define WPM thresholds (these can be adjusted)
    low_wpm = 80  # Too slow
    high_wpm = 160  # Very fast
    
    # Simple scoring based on WPM range
    fluency_score = 0
    if wpm < low_wpm:
        # Too slow, scale between 0-70 based on how close to low_wpm
        fluency_score = 70 * (wpm / low_wpm)
    elif wpm > high_wpm:
        # Too fast, scale between 70-85
        max_wpm = 200
        ratio = 1 - ((wpm - high_wpm) / (max_wpm - high_wpm))
        fluency_score = 70 + (15 * max(0, ratio))
    else:
        # In good range, scale between 85-100
        ideal_wpm = 120
        # Distance from ideal (normalized)
        dist = abs(wpm - ideal_wpm) / (high_wpm - low_wpm)
        fluency_score = 85 + (15 * (1 - min(1, dist * 2)))
    
    return {
        'fluency_score': fluency_score,
        'wpm': wpm
    }

# Main view functions
def index(request):
    """Homepage for reading progress app"""
    reading_levels = ReadingLevel.objects.all()
    featured_materials = ReadingMaterial.objects.order_by('-date_added')[:5]
    
    context = {
        'reading_levels': reading_levels,
        'featured_materials': featured_materials
    }
    
    return render(request, 'reading_progress/index.html', context)

@login_required
def dashboard(request):
    """Main dashboard for users"""
    user = request.user
    
    # Get recent reading sessions
    recent_sessions = ReadingSession.objects.filter(user=user).order_by('-started_at')[:5]
    
    # Get user progress across all levels
    progress_data = ReadingProgress.objects.filter(user=user)
    
    # Get badges earned
    badges = StudentBadge.objects.filter(user=user).order_by('-date_earned')[:5]
    
    # Calculate stats
    total_time_spent = sum(
        (session.duration_seconds() or 0) 
        for session in ReadingSession.objects.filter(user=user, is_completed=True)
    )
    total_time_display = str(timedelta(seconds=int(total_time_spent)))
    
    words_read = ReadingProgress.objects.filter(user=user).aggregate(Sum('total_words_read'))
    total_words = words_read['total_words_read__sum'] or 0
    
    context = {
        'recent_sessions': recent_sessions,
        'progress_data': progress_data,
        'badges': badges,
        'total_time': total_time_display,
        'total_words': total_words,
        'recommended_materials': get_recommended_materials(user)
    }
    
    return render(request, 'reading_progress/dashboard.html', context)

def get_recommended_materials(user):
    """Get recommended reading materials based on user's level and history"""
    # Get user's average reading level
    user_progress = ReadingProgress.objects.filter(user=user)
    
    if not user_progress.exists():
        # New user, recommend beginner materials
        beginner_level = ReadingLevel.objects.first()  # Assumes ordered by difficulty
        return ReadingMaterial.objects.filter(level=beginner_level)[:3]
    
    # Find the level the user is currently working on the most
    current_level = user_progress.order_by('-readings_completed').first().level
    
    # Get materials at that level that the user hasn't read yet
    completed_material_ids = ReadingSession.objects.filter(
        user=user, is_completed=True
    ).values_list('reading_material_id', flat=True)
    
    recommendations = ReadingMaterial.objects.filter(
        level=current_level
    ).exclude(
        id__in=completed_material_ids
    )[:3]
    
    # If not enough recommendations, add some from the next level
    if recommendations.count() < 3:
        next_level = ReadingLevel.objects.filter(id__gt=current_level.id).first()
        if next_level:
            next_level_recs = ReadingMaterial.objects.filter(
                level=next_level
            ).exclude(
                id__in=completed_material_ids
            )[:3 - recommendations.count()]
            
            recommendations = list(recommendations) + list(next_level_recs)
    
    return recommendations

def reading_material_list(request):
    """List all reading materials, with optional filtering"""
    materials = ReadingMaterial.objects.all()
    
    # Handle filters
    level_id = request.GET.get('level')
    category = request.GET.get('category')
    
    if level_id:
        materials = materials.filter(level_id=level_id)
    
    if category:
        materials = materials.filter(category=category)
    
    # Get all levels for the filter dropdown
    levels = ReadingLevel.objects.all()
    
    context = {
        'materials': materials,
        'levels': levels,
        'selected_level': level_id,
        'selected_category': category,
        'categories': ReadingMaterial.CATEGORY_CHOICES
    }
    
    return render(request, 'reading_progress/material_list.html', context)

def reading_material_by_level(request, level_id):
    """Show reading materials for a specific level"""
    level = get_object_or_404(ReadingLevel, id=level_id)
    materials = ReadingMaterial.objects.filter(level=level)
    
    context = {
        'level': level,
        'materials': materials
    }
    
    return render(request, 'reading_progress/material_by_level.html', context)

def reading_material_detail(request, material_id):
    """Show details for a specific reading material"""
    material = get_object_or_404(ReadingMaterial, id=material_id)
    
    # Check if the user has any sessions with this material
    user_sessions = None
    if request.user.is_authenticated:
        user_sessions = ReadingSession.objects.filter(
            user=request.user,
            reading_material=material
        ).order_by('-started_at')
    
    context = {
        'material': material,
        'user_sessions': user_sessions
    }
    
    return render(request, 'reading_progress/material_detail.html', context)

@login_required
def start_reading_session(request, material_id):
    """Start a new reading session"""
    material = get_object_or_404(ReadingMaterial, id=material_id)
    
    # Create a new session
    session = ReadingSession.objects.create(
        user=request.user,
        reading_material=material,
        started_at=timezone.now()
    )
    
    return redirect('reading_progress:session', session_id=session.id)

@login_required
def reading_session(request, session_id):
    """Main reading session view"""
    session = get_object_or_404(ReadingSession, id=session_id, user=request.user)
    material = session.reading_material
    
    # Check if there's already an analysis for this session
    analysis = ReadingAnalysis.objects.filter(reading_session=session).first()
    
    context = {
        'session': session,
        'material': material,
        'analysis': analysis
    }
    
    return render(request, 'reading_progress/session.html', context)

@login_required
@csrf_exempt
def save_recording(request, session_id):
    """Save the audio recording for a reading session"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    session = get_object_or_404(ReadingSession, id=session_id, user=request.user)
    
    try:
        data = json.loads(request.body)
        audio_data = data.get('audio')
        
        if not audio_data:
            return JsonResponse({'status': 'error', 'message': 'No audio data provided'}, status=400)
        
        # Save the audio file
        file_path = save_audio_file(audio_data, session_id)
        
        # Update the session with the audio file path
        relative_path = os.path.relpath(file_path, 'media')
        session.audio_recording = relative_path
        session.save()
        
        return JsonResponse({'status': 'success', 'file_path': relative_path})
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@csrf_exempt
def analyze_reading(request, session_id):
    """Analyze a reading recording"""
    session = get_object_or_404(ReadingSession, id=session_id, user=request.user)
    
    if not session.audio_recording:
        return JsonResponse({'status': 'error', 'message': 'No recording found'}, status=400)
    
    try:
        # Get the audio file path
        audio_path = os.path.join('media', session.audio_recording.name)
        
        # Transcribe the audio
        transcription = speech_to_text(audio_path)
        
        if not transcription:
            return JsonResponse({'status': 'error', 'message': 'Could not transcribe audio'}, status=400)
        
        # Calculate reading speed
        duration = session.duration_seconds() or 60  # Default to 60s if not available
        wpm = calculate_reading_speed(transcription, duration)
        
        # Analyze accuracy
        reference_text = session.reading_material.content
        accuracy_results = analyze_reading_accuracy(reference_text, transcription)
        
        # Analyze fluency
        fluency_results = analyze_fluency(transcription, duration, reference_text)
        
        # Create or update analysis record
        analysis, created = ReadingAnalysis.objects.update_or_create(
            reading_session=session,
            defaults={
                'transcription': transcription,
                'words_per_minute': wpm,
                'accuracy_percentage': accuracy_results['accuracy'],
                'mispronounced_words': accuracy_results['mispronounced_words'],
                'fluency_score': fluency_results['fluency_score'],
            }
        )
        
        # Update the user's progress
        update_user_progress(request.user, session, analysis)
        
        # Check for badges
        new_badges = check_and_award_badges(request.user)
        
        return JsonResponse({
            'status': 'success',
            'analysis_id': analysis.id,
            'wpm': wpm,
            'accuracy': accuracy_results['accuracy'],
            'fluency': fluency_results['fluency_score'],
            'transcription': transcription,
            'mispronounced_words': accuracy_results['mispronounced_words'],
            'new_badges': new_badges
        })
    
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def update_user_progress(user, session, analysis):
    """Update the user's reading progress stats"""
    # Mark the session as completed
    if not session.is_completed:
        session.mark_complete()
    
    # Get or create progress record for this level
    progress, created = ReadingProgress.objects.get_or_create(
        user=user,
        level=session.reading_material.level,
        defaults={
            'readings_completed': 0,
            'total_words_read': 0
        }
    )
    
    # Update progress
    progress.update_from_session(analysis)

def check_and_award_badges(user):
    """Check if user has earned any new badges"""
    # Get all badges
    all_badges = Badge.objects.all()
    
    # Get user's current badges
    user_badge_ids = StudentBadge.objects.filter(user=user).values_list('badge_id', flat=True)
    
    # Badges to check that the user doesn't already have
    badges_to_check = all_badges.exclude(id__in=user_badge_ids)
    
    new_badges = []
    
    for badge in badges_to_check:
        earned = False
        
        # Check different badge types
        if badge.requirement_type == 'readings_completed':
            # Total readings across all levels
            total_readings = ReadingProgress.objects.filter(user=user).aggregate(
                Sum('readings_completed')
            )['readings_completed__sum'] or 0
            
            earned = total_readings >= badge.requirement_value
            
        elif badge.requirement_type == 'wpm_achieved':
            # Check if any analysis has achieved the target WPM
            max_wpm = ReadingAnalysis.objects.filter(
                reading_session__user=user
            ).aggregate(Max('words_per_minute'))['words_per_minute__max'] or 0
            
            earned = max_wpm >= badge.requirement_value
        
        # More badge types can be added here
        
        if earned:
            # Award the badge
            student_badge = StudentBadge.objects.create(user=user, badge=badge)
            new_badges.append({
                'name': badge.name,
                'description': badge.description,
                'image_url': badge.image.url if badge.image else None
            })
    
    return new_badges

@login_required
def complete_reading_session(request, session_id):
    """Complete a reading session and show results"""
    session = get_object_or_404(ReadingSession, id=session_id, user=request.user)
    
    # Get analysis if it exists
    analysis = ReadingAnalysis.objects.filter(reading_session=session).first()
    
    if not analysis:
        # Redirect back to session if no analysis exists
        return redirect('reading_progress:session', session_id=session.id)
    
    # Mark session as completed if not already
    if not session.is_completed:
        session.mark_complete()
    
    context = {
        'session': session,
        'analysis': analysis,
        'material': session.reading_material
    }
    
    return render(request, 'reading_progress/session_results.html', context)

@login_required
def session_progress(request, session_id):
    """AJAX endpoint to get session progress data"""
    session = get_object_or_404(ReadingSession, id=session_id, user=request.user)
    analysis = ReadingAnalysis.objects.filter(reading_session=session).first()
    
    if not analysis:
        return JsonResponse({
            'has_analysis': False
        })
    
    return JsonResponse({
        'has_analysis': True,
        'wpm': analysis.words_per_minute,
        'accuracy': analysis.accuracy_percentage,
        'fluency': analysis.fluency_score
    })

@login_required
def progress_overview(request):
    """Show user's overall reading progress"""
    user = request.user
    
    # Get progress data grouped by level
    progress_by_level = ReadingProgress.objects.filter(user=user).order_by('level__name')
    
    # Get monthly stats
    last_12_months = timezone.now() - timedelta(days=365)
    monthly_sessions = ReadingSession.objects.filter(
        user=user,
        started_at__gte=last_12_months,
        is_completed=True
    ).order_by('started_at')
    
    # Process into monthly data (this is a simplified version)
    monthly_data = {}
    for session in monthly_sessions:
        month_key = session.started_at.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'count': 0,
                'words': 0
            }
        
        monthly_data[month_key]['count'] += 1
        monthly_data[month_key]['words'] += session.reading_material.word_count
    
    context = {
        'progress_by_level': progress_by_level,
        'monthly_data': monthly_data,
        'total_time': sum(session.duration_seconds() or 0 for session in monthly_sessions),
        'total_sessions': monthly_sessions.count(),
        'total_words': sum(session.reading_material.word_count for session in monthly_sessions)
    }
    
    return render(request, 'reading_progress/progress_overview.html', context)

@login_required
def reading_history(request):
    """Show user's reading history/completed sessions"""
    user = request.user
    
    # Get all completed sessions
    sessions = ReadingSession.objects.filter(
        user=user,
        is_completed=True
    ).order_by('-completed_at')
    
    context = {
        'sessions': sessions
    }
    
    return render(request, 'reading_progress/reading_history.html', context)

@login_required
def user_badges(request):
    """Show user's earned badges"""
    user = request.user
    
    # Get user's badges
    user_badges = StudentBadge.objects.filter(user=user).order_by('-date_earned')
    
    # Get all badges to show which ones are not yet earned
    all_badges = Badge.objects.all()
    earned_badge_ids = user_badges.values_list('badge_id', flat=True)
    unearned_badges = all_badges.exclude(id__in=earned_badge_ids)
    
    context = {
        'user_badges': user_badges,
        'unearned_badges': unearned_badges
    }
    
    return render(request, 'reading_progress/user_badges.html', context)

# Teacher views
@login_required
def teacher_dashboard(request):
    """Dashboard for teachers"""
    # This is a simple implementation - in a real app, you'd check if the user is a teacher
    
    # Get all students (in a real app, you'd only get students assigned to this teacher)
    students = User.objects.filter(is_staff=False, is_superuser=False)
    
    # Get some basic stats
    reading_stats = {}
    for student in students:
        reading_stats[student.id] = {
            'sessions': ReadingSession.objects.filter(user=student, is_completed=True).count(),
            'avg_accuracy': ReadingAnalysis.objects.filter(
                reading_session__user=student
            ).aggregate(Avg('accuracy_percentage'))['accuracy_percentage__avg'] or 0,
            'recent_session': ReadingSession.objects.filter(
                user=student, is_completed=True
            ).order_by('-completed_at').first()
        }
    
    context = {
        'students': students,
        'reading_stats': reading_stats
    }
    
    return render(request, 'reading_progress/teacher_dashboard.html', context)

@login_required
def student_progress(request, student_id):
    """Detailed view of a specific student's progress"""
    # This is a simple implementation - in a real app, you'd check if the user is a teacher
    # and if they have access to this student
    
    student = get_object_or_404(User, id=student_id)
    
    # Get student's progress data
    progress_data = ReadingProgress.objects.filter(user=student)
    
    # Get recent sessions
    recent_sessions = ReadingSession.objects.filter(
        user=student,
        is_completed=True
    ).order_by('-completed_at')[:10]
    
    # Calculate overall stats
    overall_stats = {
        'total_readings': sum(p.readings_completed for p in progress_data),
        'total_words': sum(p.total_words_read for p in progress_data),
        'avg_accuracy': ReadingAnalysis.objects.filter(
            reading_session__user=student
        ).aggregate(Avg('accuracy_percentage'))['accuracy_percentage__avg'] or 0,
        'avg_wpm': ReadingAnalysis.objects.filter(
            reading_session__user=student
        ).aggregate(Avg('words_per_minute'))['words_per_minute__avg'] or 0
    }
    
    context = {
        'student': student,
        'progress_data': progress_data,
        'recent_sessions': recent_sessions,
        'overall_stats': overall_stats
    }
    
    return render(request, 'reading_progress/student_progress.html', context)

@login_required
def class_overview(request):
    """Overview of all students' progress"""
    # This is a simple implementation - in a real app, you'd check if the user is a teacher
    # and only show students in their class
    
    # Get all students
    students = User.objects.filter(is_staff=False, is_superuser=False)
    
    # Collect reading level distribution
    level_distribution = {}
    levels = ReadingLevel.objects.all()
    
    for level in levels:
        level_distribution[level.id] = 0
    
    for student in students:
        # Get the student's highest level with at least 3 completed readings
        top_level = ReadingProgress.objects.filter(
            user=student,
            readings_completed__gte=3  # Adjust this threshold as needed
        ).order_by('-level__id').first()
        
        if top_level:
            level_distribution[top_level.level.id] += 1
    
    # Get overall class stats
    class_stats = {
        'total_sessions': ReadingSession.objects.filter(is_completed=True).count(),
        'avg_accuracy': ReadingAnalysis.objects.all().aggregate(
            Avg('accuracy_percentage')
        )['accuracy_percentage__avg'] or 0,
        'avg_wpm': ReadingAnalysis.objects.all().aggregate(
            Avg('words_per_minute')
        )['words_per_minute__avg'] or 0,
        'total_words': ReadingProgress.objects.all().aggregate(
            Sum('total_words_read')
        )['total_words_read__sum'] or 0
    }
    
    context = {
        'students': students,
        'levels': levels,
        'level_distribution': level_distribution,
        'class_stats': class_stats
    }
    
    return render(request, 'reading_progress/class_overview.html', context)
