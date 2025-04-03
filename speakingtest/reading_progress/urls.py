from django.urls import path
from . import views

app_name = 'reading_progress'

urlpatterns = [
    # Main dashboard views
    path('', views.index, name='index'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Reading materials
    path('reading-materials/', views.reading_material_list, name='material_list'),
    path('reading-materials/<int:level_id>/', views.reading_material_by_level, name='material_by_level'),
    path('reading-material/<int:material_id>/', views.reading_material_detail, name='material_detail'),
    
    # Reading sessions
    path('start-session/<int:material_id>/', views.start_reading_session, name='start_session'),
    path('session/<int:session_id>/', views.reading_session, name='session'),
    path('complete-session/<int:session_id>/', views.complete_reading_session, name='complete_session'),
    
    # API endpoints for AJAX calls
    path('api/save-recording/<int:session_id>/', views.save_recording, name='save_recording'),
    path('api/analyze-reading/<int:session_id>/', views.analyze_reading, name='analyze_reading'),
    path('api/session-progress/<int:session_id>/', views.session_progress, name='session_progress'),
    
    # Progress tracking
    path('progress/', views.progress_overview, name='progress_overview'),
    path('progress/history/', views.reading_history, name='reading_history'),
    path('badges/', views.user_badges, name='user_badges'),
    
    # Teacher views
    path('teacher/dashboard/', views.teacher_dashboard, name='teacher_dashboard'),
    path('teacher/student/<int:student_id>/', views.student_progress, name='student_progress'),
    path('teacher/class-overview/', views.class_overview, name='class_overview'),
]
