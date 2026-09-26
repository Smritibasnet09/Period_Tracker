"""
LunaFlow Predictions Models

Prediction: stores a generated period prediction (separate from actual data).
PredictionEvaluation: tracks predicted vs actual when reality becomes known.
ModelMetrics: aggregated ML model performance per user.
"""
from django.db import models
from django.conf import settings


class Prediction(models.Model):
    """A generated prediction for the user's next period."""

    MODEL_CHOICES = [
        ('baseline', 'Baseline (Population Average)'),
        ('statistical', 'Statistical (Weighted Average)'),
        ('linear_regression', 'Linear Regression'),
        ('random_forest', 'Random Forest'),
        ('gradient_boosting', 'Gradient Boosting'),
        ('xgboost', 'XGBoost'),
        ('lightgbm', 'LightGBM'),
    ]

    CONFIDENCE_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='predictions'
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    predicted_start_date = models.DateField()
    predicted_end_date = models.DateField()
    predicted_cycle_length = models.IntegerField()
    uncertainty_days = models.IntegerField(default=2)
    model_used = models.CharField(max_length=30, choices=MODEL_CHOICES, default='baseline')
    confidence_level = models.CharField(max_length=10, choices=CONFIDENCE_CHOICES, default='low')
    explanation = models.JSONField(default=dict)   # {text, factors, trend_message, etc.}
    factors_used = models.JSONField(default=list)  # list of factor names
    cycles_used_count = models.IntegerField(default=0)
    fertile_window_start = models.DateField(null=True, blank=True)
    fertile_window_end = models.DateField(null=True, blank=True)
    estimated_ovulation = models.DateField(null=True, blank=True)
    is_latest = models.BooleanField(default=True)

    class Meta:
        db_table = 'predictions'
        ordering = ['-generated_at']
        verbose_name = 'Prediction'
        verbose_name_plural = 'Predictions'

    def __str__(self):
        return f"Prediction for {self.user.email}: {self.predicted_start_date} (±{self.uncertainty_days}d)"


class PredictionEvaluation(models.Model):
    """Tracks how accurate a past prediction was, once the actual period arrives."""

    prediction = models.OneToOneField(
        Prediction, on_delete=models.CASCADE, related_name='evaluation'
    )
    actual_cycle = models.ForeignKey(
        'cycles.Cycle', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prediction_evaluations'
    )
    predicted_start = models.DateField()
    actual_start = models.DateField(null=True, blank=True)
    difference_days = models.IntegerField(null=True, blank=True)
    evaluated_at = models.DateTimeField(auto_now_add=True)
    was_accurate = models.BooleanField(null=True, blank=True)  # True if |diff| <= 2 days

    class Meta:
        db_table = 'prediction_evaluations'
        ordering = ['-evaluated_at']

    def save(self, *args, **kwargs):
        if self.actual_start and self.predicted_start:
            from datetime import datetime
            self.difference_days = (self.actual_start - self.predicted_start).days
            self.was_accurate = abs(self.difference_days) <= 2
        super().save(*args, **kwargs)

    def __str__(self):
        diff = f"{self.difference_days:+d} days" if self.difference_days is not None else "pending"
        return f"Eval: {self.predicted_start} → {self.actual_start} ({diff})"


class ModelMetrics(models.Model):
    """Aggregated ML model performance metrics per user."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='model_metrics'
    )
    evaluated_at = models.DateTimeField(auto_now_add=True)
    mae_days = models.FloatField()
    rmse_days = models.FloatField(null=True, blank=True)
    model_type = models.CharField(max_length=30)
    cycles_evaluated = models.IntegerField()
    accuracy_within_2_days = models.FloatField()  # percentage

    class Meta:
        db_table = 'model_metrics'
        ordering = ['-evaluated_at']

    def __str__(self):
        return f"Metrics for {self.user.email} ({self.model_type}): MAE={self.mae_days:.1f}d"
