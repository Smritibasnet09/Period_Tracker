"""LunaFlow Cycles Serializers"""
from rest_framework import serializers
from .models import Cycle, FlowLog


class FlowLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FlowLog
        fields = ['id', 'cycle', 'date', 'intensity', 'color', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        # Ensure cycle belongs to the requesting user
        request = self.context.get('request')
        if request and data.get('cycle') and data['cycle'].user != request.user:
            raise serializers.ValidationError("Invalid cycle.")
        return data


class CycleSerializer(serializers.ModelSerializer):
    """Full cycle serializer including flow logs."""
    flow_logs = FlowLogSerializer(many=True, read_only=True)
    current_day = serializers.ReadOnlyField()

    class Meta:
        model = Cycle
        fields = [
            'id', 'start_date', 'end_date', 'cycle_length',
            'period_start', 'period_end', 'period_duration',
            'notes', 'is_active', 'current_day', 'flow_logs',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'cycle_length', 'period_duration', 'current_day',
                            'created_at', 'updated_at']


class CycleCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating a new cycle (logging period start)."""

    class Meta:
        model = Cycle
        fields = ['start_date', 'period_start', 'period_end', 'notes']

    def validate_start_date(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Cycle start date cannot be in the future.")
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        # Deactivate the current active cycle and set its end_date
        active_cycle = Cycle.objects.filter(user=user, is_active=True).first()
        if active_cycle:
            active_cycle.end_date = validated_data['start_date']
            active_cycle.is_active = False
            active_cycle.save()

        validated_data['period_start'] = validated_data.get('period_start', validated_data['start_date'])
        return Cycle.objects.create(user=user, is_active=True, **validated_data)


class CycleUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating a cycle (e.g., setting period_end)."""

    class Meta:
        model = Cycle
        fields = ['period_end', 'notes']


class CycleStatsSerializer(serializers.Serializer):
    """Serializer for insights/cycle statistics."""
    avg_cycle_length = serializers.FloatField(allow_null=True)
    median_cycle_length = serializers.FloatField(allow_null=True)
    min_cycle_length = serializers.IntegerField(allow_null=True)
    max_cycle_length = serializers.IntegerField(allow_null=True)
    std_cycle_length = serializers.FloatField(allow_null=True)
    avg_period_duration = serializers.FloatField(allow_null=True)
    cycle_count = serializers.IntegerField()
    regularity_score = serializers.FloatField(allow_null=True)
    recent_trend = serializers.CharField(allow_null=True)
    personalized_insights = serializers.ListField(child=serializers.CharField())
    anomaly_detected = serializers.BooleanField()
    anomaly_message = serializers.CharField(allow_null=True)
    cycle_history = CycleSerializer(many=True)
