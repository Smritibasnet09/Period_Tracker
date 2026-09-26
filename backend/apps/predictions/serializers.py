"""LunaFlow Predictions Serializers"""
from rest_framework import serializers
from .models import Prediction, PredictionEvaluation, ModelMetrics


class PredictionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prediction
        fields = [
            'id', 'generated_at', 'predicted_start_date', 'predicted_end_date',
            'predicted_cycle_length', 'uncertainty_days', 'model_used',
            'confidence_level', 'explanation', 'factors_used', 'cycles_used_count',
            'fertile_window_start', 'fertile_window_end', 'estimated_ovulation',
            'is_latest',
        ]
        read_only_fields = fields


class PredictionEvaluationSerializer(serializers.ModelSerializer):
    model_used = serializers.CharField(source='prediction.model_used', read_only=True)
    confidence_level = serializers.CharField(source='prediction.confidence_level', read_only=True)

    class Meta:
        model = PredictionEvaluation
        fields = [
            'id', 'predicted_start', 'actual_start', 'difference_days',
            'was_accurate', 'evaluated_at', 'model_used', 'confidence_level',
        ]


class ModelMetricsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMetrics
        fields = [
            'id', 'evaluated_at', 'mae_days', 'rmse_days',
            'model_type', 'cycles_evaluated', 'accuracy_within_2_days',
        ]
