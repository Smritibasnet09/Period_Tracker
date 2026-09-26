"""
LunaFlow Cycles Models

Cycle: represents one full menstrual cycle (start of one period to start of next).
FlowLog: daily flow intensity entries within a period.
"""
from django.db import models
from django.conf import settings


class Cycle(models.Model):
    """Represents one complete menstrual cycle for a user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cycles'
    )
    # Cycle boundaries (start of period → start of next period)
    start_date = models.DateField(help_text="First day of period (cycle start)")
    end_date = models.DateField(
        null=True, blank=True,
        help_text="First day of next period (cycle end — set when next cycle begins)"
    )
    cycle_length = models.IntegerField(
        null=True, blank=True,
        help_text="Computed: end_date - start_date in days"
    )

    # Period within this cycle
    period_start = models.DateField(help_text="First day of menstrual bleeding")
    period_end = models.DateField(null=True, blank=True, help_text="Last day of bleeding")
    period_duration = models.IntegerField(null=True, blank=True)

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, help_text="True for the current ongoing cycle")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cycles'
        ordering = ['-start_date']
        verbose_name = 'Cycle'
        verbose_name_plural = 'Cycles'

    def __str__(self):
        return f"Cycle for {self.user.email} starting {self.start_date}"

    def save(self, *args, **kwargs):
        # Auto-compute cycle_length and period_duration
        if self.start_date and self.end_date:
            self.cycle_length = (self.end_date - self.start_date).days
        if self.period_start and self.period_end:
            self.period_duration = (self.period_end - self.period_start).days + 1
        super().save(*args, **kwargs)

    @property
    def current_day(self):
        """Returns the current day number in this cycle (1-indexed)."""
        from datetime import date
        if self.is_active:
            delta = (date.today() - self.start_date).days
            return max(1, delta + 1)
        return None


class FlowLog(models.Model):
    """Daily flow intensity record during a period."""

    INTENSITY_CHOICES = [
        ('spotting', 'Spotting'),
        ('light', 'Light'),
        ('medium', 'Medium'),
        ('heavy', 'Heavy'),
    ]

    COLOR_CHOICES = [
        ('bright_red', 'Bright Red'),
        ('dark_red', 'Dark Red'),
        ('brown', 'Brown'),
        ('pink', 'Pink'),
        ('orange', 'Orange'),
    ]

    cycle = models.ForeignKey(Cycle, on_delete=models.CASCADE, related_name='flow_logs')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='flow_logs'
    )
    date = models.DateField()
    intensity = models.CharField(max_length=20, choices=INTENSITY_CHOICES, default='medium')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'flow_logs'
        unique_together = ['user', 'date']
        ordering = ['-date']

    def __str__(self):
        return f"{self.user.email} - {self.date} ({self.intensity})"
