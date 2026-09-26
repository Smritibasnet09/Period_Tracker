"""LunaFlow Logs Admin"""
from django.contrib import admin
from .models import DailyLog, Symptom


class SymptomInline(admin.TabularInline):
    model = Symptom
    extra = 0


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'mood', 'energy', 'stress', 'sleep_hours']
    list_filter = ['date', 'mood']
    search_fields = ['user__email']
    ordering = ['-date']
    inlines = [SymptomInline]


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ['daily_log', 'symptom_type', 'severity']
    list_filter = ['symptom_type', 'severity']
