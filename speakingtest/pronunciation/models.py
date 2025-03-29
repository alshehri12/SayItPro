from django.db import models

class Sentence(models.Model):
    """Model to store English sentences for pronunciation practice."""
    text = models.TextField(help_text="The sentence for pronunciation practice")
    difficulty = models.CharField(max_length=20, choices=[
        ('easy', 'Easy'),
        ('medium', 'Medium'),
        ('hard', 'Hard'),
    ], default='medium')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.text[:50] + '...' if len(self.text) > 50 else self.text
