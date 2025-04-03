from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

class ReadingLevel(models.Model):
    name = models.CharField(max_length=50)  # e.g., 'Beginner', 'Intermediate', 'Advanced'
    grade_equivalent = models.CharField(max_length=20, blank=True)  # e.g., '3rd Grade'
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

class ReadingMaterial(models.Model):
    CATEGORY_CHOICES = [
        ('fiction', 'Fiction'),
        ('non_fiction', 'Non-Fiction'),
        ('poetry', 'Poetry'),
        ('technical', 'Technical'),
        ('news', 'News Article'),
    ]
    
    title = models.CharField(max_length=255)
    content = models.TextField()
    level = models.ForeignKey(ReadingLevel, on_delete=models.CASCADE)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='fiction')
    author = models.CharField(max_length=100, blank=True)
    word_count = models.PositiveIntegerField()
    estimated_time_minutes = models.PositiveIntegerField(default=5)
    date_added = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        # Auto-calculate word count if not provided
        if not self.word_count:
            self.word_count = len(self.content.split())
        super().save(*args, **kwargs)

class ReadingSession(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    reading_material = models.ForeignKey(ReadingMaterial, on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    audio_recording = models.FileField(upload_to='reading_recordings/%Y/%m/%d/', null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    
    def duration_seconds(self):
        if self.is_completed and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def mark_complete(self):
        self.completed_at = timezone.now()
        self.is_completed = True
        self.save()
    
    def __str__(self):
        return f"{self.user.username} - {self.reading_material.title}"

class ReadingAnalysis(models.Model):
    reading_session = models.OneToOneField(ReadingSession, on_delete=models.CASCADE)
    transcription = models.TextField(blank=True)
    words_per_minute = models.FloatField(null=True, blank=True)
    accuracy_percentage = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)], 
        null=True, blank=True
    )
    mispronounced_words = models.JSONField(default=dict, blank=True)
    fluency_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True
    )
    comprehension_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        null=True, blank=True
    )
    
    def __str__(self):
        return f"Analysis of {self.reading_session}"

class ReadingProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    level = models.ForeignKey(ReadingLevel, on_delete=models.CASCADE)
    readings_completed = models.PositiveIntegerField(default=0)
    total_words_read = models.PositiveIntegerField(default=0)
    average_wpm = models.FloatField(null=True, blank=True)
    average_accuracy = models.FloatField(null=True, blank=True)
    last_reading_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        unique_together = ('user', 'level')
    
    def __str__(self):
        return f"{self.user.username}'s progress at {self.level.name} level"
    
    def update_from_session(self, reading_analysis):
        """Update progress based on completed reading session"""
        session = reading_analysis.reading_session
        
        # Only update for completed sessions
        if not session.is_completed:
            return
            
        # Update counts
        self.readings_completed += 1
        self.total_words_read += session.reading_material.word_count
        self.last_reading_date = timezone.now()
        
        # Update averages
        if reading_analysis.words_per_minute:
            if not self.average_wpm:
                self.average_wpm = reading_analysis.words_per_minute
            else:
                self.average_wpm = (self.average_wpm * (self.readings_completed - 1) + 
                                 reading_analysis.words_per_minute) / self.readings_completed
        
        if reading_analysis.accuracy_percentage:
            if not self.average_accuracy:
                self.average_accuracy = reading_analysis.accuracy_percentage
            else:
                self.average_accuracy = (self.average_accuracy * (self.readings_completed - 1) + 
                                       reading_analysis.accuracy_percentage) / self.readings_completed
        
        self.save()

class Badge(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='badges/')
    requirement_type = models.CharField(max_length=50)  # e.g., 'readings_completed', 'wpm_achieved'
    requirement_value = models.PositiveIntegerField()  # e.g., 10 readings, 120 wpm
    
    def __str__(self):
        return self.name

class StudentBadge(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    date_earned = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'badge')
    
    def __str__(self):
        return f"{self.user.username} earned {self.badge.name}"
