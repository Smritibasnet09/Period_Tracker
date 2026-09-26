"""LunaFlow Reminders Serializers"""
from rest_framework import serializers
from .models import Reminder


class ReminderSerializer(serializers.ModelSerializer):
    reminder_type_display = serializers.CharField(
        source='get_reminder_type_display', read_only=True
    )

    class Meta:
        model = Reminder
        fields = [
            'id', 'reminder_type', 'reminder_type_display', 'days_before',
            'time_of_day', 'is_active', 'label', 'custom_message',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
