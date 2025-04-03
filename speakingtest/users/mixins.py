from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse_lazy

class AdminRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to require an admin user"""
    
    def test_func(self):
        return self.request.user.is_admin()
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("You don't have permission to access this page.")
        
class TeacherRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to require a teacher user"""
    
    def test_func(self):
        return self.request.user.is_teacher() or self.request.user.is_admin()
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("You don't have permission to access this page.")
        
class StudentRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin to require a student user"""
    
    def test_func(self):
        return self.request.user.is_student()
    
    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        raise PermissionDenied("You don't have permission to access this page.")

def role_redirect(request):
    """Redirect users to their appropriate dashboard based on role"""
    if not request.user.is_authenticated:
        return redirect('login')
        
    if request.user.is_admin():
        return redirect('admin_dashboard')
    elif request.user.is_teacher():
        return redirect('teacher_dashboard')
    else:  # Student
        return redirect('student_dashboard')
