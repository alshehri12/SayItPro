from django.urls import path
from . import views
from .mixins import role_redirect

urlpatterns = [
    path('', views.home, name='home'),
    path('role-redirect/', views.home, name='role_redirect'),  # This will use the role_redirect function via views.home
    path('admin-dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('teacher-dashboard/', views.TeacherDashboardView.as_view(), name='teacher_dashboard'),
    path('student-dashboard/', views.StudentDashboardView.as_view(), name='student_dashboard'),
    path('students/', views.StudentListView.as_view(), name='student_list'),
    path('students/<int:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
]
