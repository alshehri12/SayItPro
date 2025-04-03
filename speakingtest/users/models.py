from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """Custom user model with role-based permissions"""
    # Role choices
    ADMIN = 'admin'
    TEACHER = 'teacher'
    STUDENT = 'student'
    
    ROLE_CHOICES = (
        (ADMIN, _('Admin')),
        (TEACHER, _('Teacher')),
        (STUDENT, _('Student')),
    )
    
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default=STUDENT,
        verbose_name=_('Role'),
    )
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For Teacher-Student relationship
    teacher = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='students',
        limit_choices_to={'role': TEACHER}
    )
    
    def is_admin(self):
        return self.role == self.ADMIN or self.is_superuser
    
    def is_teacher(self):
        return self.role == self.TEACHER
    
    def is_student(self):
        return self.role == self.STUDENT
    
    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"
