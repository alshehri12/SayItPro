from django.contrib import admin
from .models import Sentence

@admin.register(Sentence)
class SentenceAdmin(admin.ModelAdmin):
    list_display = ('text', 'difficulty', 'created_at')
    list_filter = ('difficulty', 'created_at')
    search_fields = ('text',)
