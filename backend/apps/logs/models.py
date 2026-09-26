"""
LunaFlow Daily Log Models

DailyLog: one per user per day — mood, energy, sleep, stress, etc.
Symptom: specific symptoms attached to a daily log entry.
"""
from django.db import models
from django.conf import settings


class DailyLog(models.Model):
    """Daily health tracking entry — one per user per date."""

    MOOD_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1=terrible, 5=great
    LEVEL_CHOICES = [(i, str(i)) for i in range(1, 6)]  # 1=very low, 5=very high

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='daily_logs'
    )
    date = models.DateField()
    mood = models.IntegerField(choices=MOOD_CHOICES, null=True, blank=True)
    energy = models.IntegerField(choices=LEVEL_CHOICES, null=True, blank=True)
    stress = models.IntegerField(choices=LEVEL_CHOICES, null=True, blank=True)
    sleep_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    exercise_minutes = models.IntegerField(null=True, blank=True, default=0)
    appetite = models.IntegerField(choices=LEVEL_CHOICES, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'daily_logs'
        unique_together = ['user', 'date']
        ordering = ['-date']
        verbose_name = 'Daily Log'
        verbose_name_plural = 'Daily Logs'

    def __str__(self):
        return f"{self.user.email} — {self.date}"


class Symptom(models.Model):
    """A specific symptom recorded for a particular daily log."""

    SYMPTOM_CHOICES = [
        ('cramps', 'Cramps'),
        ('headache', 'Headache'),
        ('acne', 'Acne'),
        ('bloating', 'Bloating'),
        ('breast_tenderness', 'Breast Tenderness'),
        ('fatigue', 'Fatigue'),
        ('nausea', 'Nausea'),
        ('spotting', 'Spotting'),
        ('discharge', 'Discharge'),
        ('back_pain', 'Back Pain'),
        ('insomnia', 'Insomnia'),
        ('mood_swings', 'Mood Swings'),
    ]

    SEVERITY_CHOICES = [
        (1, 'Mild'),
        (2, 'Moderate'),
        (3, 'Severe'),
    ]

    daily_log = models.ForeignKey(
        DailyLog, on_delete=models.CASCADE, related_name='symptoms'
    )
    symptom_type = models.CharField(max_length=30, choices=SYMPTOM_CHOICES)
    severity = models.IntegerField(choices=SEVERITY_CHOICES, default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'symptoms'
        unique_together = ['daily_log', 'symptom_type']
        verbose_name = 'Symptom'
        verbose_name_plural = 'Symptoms'

    def __str__(self):
        return f"{self.symptom_type} (severity {self.severity}) on {self.daily_log.date}"
