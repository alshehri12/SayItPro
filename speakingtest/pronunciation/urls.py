from django.urls import path
from . import views

app_name = 'pronunciation'  # Define the namespace for the pronunciation app

urlpatterns = [
    path('', views.speech_to_text, name='index'),  # Speech-to-text is now the homepage with name 'index'
    path('old-home/', views.home, name='old_home'),  # Keep the old homepage accessible
    path('api/random-sentence/', views.get_random_sentence, name='random_sentence'),
    path('api/evaluate-pronunciation/', views.evaluate_pronunciation, name='evaluate_pronunciation'),
]
