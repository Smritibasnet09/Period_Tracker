"""LunaFlow Predictions Admin"""
from django.contrib import admin
from .models import Prediction, PredictionEvaluation, ModelMetrics


@admin.register(Prediction)
class PredictionAdmin(admin.ModelAdmin):
    list_display = ['user', 'predicted_start_date', 'predicted_cycle_length',
                    'uncertainty_days', 'model_used', 'confidence_level', 'is_latest']
    list_filter = ['model_used', 'confidence_level', 'is_latest']
    search_fields = ['user__email']
    ordering = ['-generated_at']


@admin.register(PredictionEvaluation)
class PredictionEvaluationAdmin(admin.ModelAdmin):
    list_display = ['prediction', 'predicted_start', 'actual_start', 'difference_days', 'was_accurate']
    list_filter = ['was_accurate']


@admin.register(ModelMetrics)
class ModelMetricsAdmin(admin.ModelAdmin):
    list_display = ['user', 'model_type', 'mae_days', 'accuracy_within_2_days', 'cycles_evaluated']
