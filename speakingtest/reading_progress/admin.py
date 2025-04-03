from django.contrib import admin
from . import models

@admin.register(models.ReadingLevel)
class ReadingLevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade_equivalent')
    search_fields = ('name', 'grade_equivalent')

@admin.register(models.ReadingMaterial)
class ReadingMaterialAdmin(admin.ModelAdmin):
    list_display = ('title', 'level', 'category', 'word_count', 'estimated_time_minutes')
    list_filter = ('level', 'category')
    search_fields = ('title', 'author', 'content')

@admin.register(models.ReadingSession)
class ReadingSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'reading_material', 'started_at', 'is_completed')
    list_filter = ('is_completed', 'started_at')
    search_fields = ('user__username', 'reading_material__title')

@admin.register(models.ReadingAnalysis)
class ReadingAnalysisAdmin(admin.ModelAdmin):
    list_display = ('reading_session', 'words_per_minute', 'accuracy_percentage', 'fluency_score')
    search_fields = ('reading_session__user__username', 'reading_session__reading_material__title')

@admin.register(models.ReadingProgress)
class ReadingProgressAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'readings_completed', 'average_wpm', 'average_accuracy')
    list_filter = ('level',)
    search_fields = ('user__username',)

@admin.register(models.Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ('name', 'requirement_type', 'requirement_value')
    search_fields = ('name', 'description')

@admin.register(models.StudentBadge)
class StudentBadgeAdmin(admin.ModelAdmin):
    list_display = ('user', 'badge', 'date_earned')
    list_filter = ('badge', 'date_earned')
    search_fields = ('user__username', 'badge__name')
