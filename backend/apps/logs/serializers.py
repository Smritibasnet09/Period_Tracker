"""LunaFlow Logs Serializers"""
from rest_framework import serializers
from .models import DailyLog, Symptom


class SymptomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symptom
        fields = ['id', 'symptom_type', 'severity', 'created_at']
        read_only_fields = ['id', 'created_at']


class DailyLogSerializer(serializers.ModelSerializer):
    """Full log serializer with nested symptoms."""
    symptoms = SymptomSerializer(many=True, required=False)

    class Meta:
        model = DailyLog
        fields = [
            'id', 'date', 'mood', 'energy', 'stress',
            'sleep_hours', 'exercise_minutes', 'appetite',
            'notes', 'symptoms', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        symptoms_data = validated_data.pop('symptoms', [])
        log = DailyLog.objects.create(**validated_data)
        for symptom in symptoms_data:
            Symptom.objects.create(daily_log=log, **symptom)
        return log

    def update(self, instance, validated_data):
        symptoms_data = validated_data.pop('symptoms', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        if symptoms_data is not None:
            # Replace all symptoms for this log
            instance.symptoms.all().delete()
            for symptom in symptoms_data:
                Symptom.objects.create(daily_log=instance, **symptom)

        return instance


class DailyLogListSerializer(serializers.ModelSerializer):
    """Lightweight list serializer."""
    symptom_count = serializers.SerializerMethodField()

    class Meta:
        model = DailyLog
        fields = ['id', 'date', 'mood', 'energy', 'stress', 'sleep_hours', 'symptom_count']

    def get_symptom_count(self, obj):
        return obj.symptoms.count()
