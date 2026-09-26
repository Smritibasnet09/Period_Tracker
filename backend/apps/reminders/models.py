"""LunaFlow Reminders Model"""
from django.db import models
from django.conf import settings


class Reminder(models.Model):
    """Stores user reminder settings for period, fertile window, daily log, and custom alerts."""

    TYPE_CHOICES = [
        ('period', 'Period Reminder'),
        ('fertile_window', 'Fertile Window Reminder'),
        ('daily_log', 'Daily Log Reminder'),
        ('custom', 'Custom Reminder'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reminders'
    )
    reminder_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    days_before = models.IntegerField(
        default=2,
        help_text="Days before period/fertile window to trigger reminder"
    )
    time_of_day = models.TimeField(default='08:00:00')
    is_active = models.BooleanField(default=True)
    label = models.CharField(max_length=100, blank=True)
    custom_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reminders'
        ordering = ['reminder_type', '-created_at']
        verbose_name = 'Reminder'
        verbose_name_plural = 'Reminders'

    def __str__(self):
        active = "✓" if self.is_active else "✗"
        return f"[{active}] {self.get_reminder_type_display()} for {self.user.email}"
