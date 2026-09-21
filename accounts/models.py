from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Custom user model for PulseWorkspace SaaS.
    Allows profile personalization, role titles, and consistent avatar colors.
    """
    role_title = models.CharField(max_length=100, blank=True, default='Software Engineer')
    avatar_color = models.CharField(max_length=20, default='#4f46e5')
    bio = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['username']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.username})"

    @property
    def display_name(self):
        full = self.get_full_name()
        return full if full else self.username

    @property
    def initials(self):
        if self.first_name and self.last_name:
            return f"{self.first_name[0]}{self.last_name[0]}".upper()
        if self.username:
            return self.username[:2].upper()
        return "U"
