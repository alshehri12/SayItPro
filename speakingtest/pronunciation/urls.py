from django.urls import path
from . import views

urlpatterns = [
    path('', views.speech_to_text, name='home'),  # Speech-to-text is now the homepage
    path('old-home/', views.home, name='old_home'),  # Keep the old homepage accessible
    path('api/random-sentence/', views.get_random_sentence, name='random_sentence'),
    path('api/evaluate-pronunciation/', views.evaluate_pronunciation, name='evaluate_pronunciation'),
]
