"""
LunaFlow Accounts Models

Defines the custom User model (email-based auth) and UserPreferences.
"""
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom User model using email as the unique identifier."""

    username = None  # Remove username field
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email


class UserPreferences(models.Model):
    """Stores user preferences for cycle tracking and notifications."""

    AGE_RANGE_CHOICES = [
        ('under_18', 'Under 18'),
        ('18_25', '18–25'),
        ('26_35', '26–35'),
        ('36_45', '36–45'),
        ('over_45', 'Over 45'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preferences')
    cycle_length_default = models.IntegerField(default=28)
    period_duration_default = models.IntegerField(default=5)
    age_range = models.CharField(max_length=20, choices=AGE_RANGE_CHOICES, blank=True)
    tracking_goals = models.JSONField(default=list)  # e.g. ['period_tracking', 'fertility']
    timezone = models.CharField(max_length=50, default='UTC')
    last_period_date = models.DateField(null=True, blank=True)

    # Reminder settings
    reminder_period_days_before = models.IntegerField(default=2)
    reminder_fertile_enabled = models.BooleanField(default=True)
    reminder_daily_log_enabled = models.BooleanField(default=True)
    reminder_daily_log_time = models.TimeField(default='08:00:00')

    onboarding_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_preferences'
        verbose_name = 'User Preferences'

    def __str__(self):
        return f"Preferences for {self.user.email}"


class DataExportRequest(models.Model):
    """Tracks data export requests for GDPR compliance."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='export_requests')
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    download_url = models.URLField(blank=True)

    class Meta:
        db_table = 'data_export_requests'
        ordering = ['-requested_at']

    def __str__(self):
        return f"Export for {self.user.email} ({self.status})"
