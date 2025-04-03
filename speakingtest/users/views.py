from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Avg, Count, Q

from .mixins import AdminRequiredMixin, TeacherRequiredMixin, StudentRequiredMixin, role_redirect
from .models import User
from reading_progress.models import ReadingSession, ReadingProgress, ReadingMaterial, ReadingAnalysis, Badge, StudentBadge

@login_required
def home(request):
    """Redirect to role-specific dashboard"""
    return role_redirect(request)

class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Dashboard for administrators"""
    template_name = 'users/admin_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get statistics for the admin dashboard
        context['total_students'] = User.objects.filter(role=User.STUDENT).count()
        context['total_teachers'] = User.objects.filter(role=User.TEACHER).count()
        context['total_reading_materials'] = ReadingMaterial.objects.count()
        context['total_reading_sessions'] = ReadingSession.objects.count()
        
        # Recent user activities
        context['recent_sessions'] = ReadingSession.objects.order_by('-start_time')[:10]
        
        # Teachers list for admin to manage
        context['teachers'] = User.objects.filter(role=User.TEACHER).order_by('username')
        
        return context

class TeacherDashboardView(TeacherRequiredMixin, TemplateView):
    """Dashboard for teachers"""
    template_name = 'users/teacher_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get teacher's students
        teacher = self.request.user
        students = User.objects.filter(teacher=teacher, role=User.STUDENT)
        context['students'] = students
        context['students_count'] = students.count()
        
        # Get recent sessions from the teacher's students
        recent_sessions = ReadingSession.objects.filter(
            user__in=students
        ).order_by('-start_time')[:10]
        context['recent_sessions'] = recent_sessions
        
        # Get average statistics for students
        student_progress = ReadingProgress.objects.filter(user__in=students)
        if student_progress.exists():
            context['avg_wpm'] = student_progress.aggregate(Avg('avg_wpm'))['avg_wpm__avg']
            context['avg_accuracy'] = student_progress.aggregate(Avg('avg_accuracy'))['avg_accuracy__avg']
            context['avg_fluency'] = student_progress.aggregate(Avg('avg_fluency'))['avg_fluency__avg']
        
        return context

class StudentListView(TeacherRequiredMixin, ListView):
    """List of students for a teacher"""
    model = User
    template_name = 'users/student_list.html'
    context_object_name = 'students'
    
    def get_queryset(self):
        if self.request.user.is_admin():
            # Admin can see all students
            return User.objects.filter(role=User.STUDENT)
        else:
            # Teacher can only see their students
            return User.objects.filter(teacher=self.request.user, role=User.STUDENT)

class StudentDetailView(TeacherRequiredMixin, DetailView):
    """View student details and progress"""
    model = User
    template_name = 'users/student_detail.html'
    context_object_name = 'student'
    
    def get_queryset(self):
        if self.request.user.is_admin():
            # Admin can see all students
            return User.objects.filter(role=User.STUDENT)
        else:
            # Teacher can only see their students
            return User.objects.filter(teacher=self.request.user, role=User.STUDENT)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        
        # Get student's reading sessions
        sessions = ReadingSession.objects.filter(user=student).order_by('-start_time')
        context['sessions'] = sessions
        context['sessions_count'] = sessions.count()
        
        # Get student's progress
        try:
            progress = ReadingProgress.objects.get(user=student)
            context['progress'] = progress
        except ReadingProgress.DoesNotExist:
            context['progress'] = None
        
        # Get student's badges
        badges = StudentBadge.objects.filter(user=student)
        context['badges'] = badges
        
        return context

class StudentDashboardView(StudentRequiredMixin, TemplateView):
    """Dashboard for students"""
    template_name = 'users/student_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.request.user
        
        # Get student's reading sessions
        sessions = ReadingSession.objects.filter(user=student).order_by('-start_time')
        context['recent_sessions'] = sessions[:5]
        context['total_sessions'] = sessions.count()
        
        # Get student's progress
        try:
            progress = ReadingProgress.objects.get(user=student)
            context['progress'] = progress
        except ReadingProgress.DoesNotExist:
            context['progress'] = None
        
        # Get suggested materials based on student's level
        if progress:
            suggested_materials = ReadingMaterial.objects.filter(
                level__level__lte=progress.current_level + 1,
                level__level__gte=progress.current_level - 1
            )[:5]
        else:
            # For new students, suggest starter materials
            suggested_materials = ReadingMaterial.objects.filter(level__level__lte=2)[:5]
        
        context['suggested_materials'] = suggested_materials
        
        # Get badges
        badges = StudentBadge.objects.filter(user=student)
        context['badges'] = badges
        
        return context
