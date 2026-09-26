"""LunaFlow Reminders Admin"""
from django.contrib import admin
from .models import Reminder


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ['user', 'reminder_type', 'days_before', 'time_of_day', 'is_active']
    list_filter = ['reminder_type', 'is_active']
    search_fields = ['user__email', 'label']
