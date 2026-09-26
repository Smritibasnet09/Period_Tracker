"""LunaFlow Cycles Admin"""
from django.contrib import admin
from .models import Cycle, FlowLog


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    list_display = ['user', 'start_date', 'end_date', 'cycle_length', 'period_duration', 'is_active']
    list_filter = ['is_active', 'start_date']
    search_fields = ['user__email']
    ordering = ['-start_date']


@admin.register(FlowLog)
class FlowLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'date', 'intensity', 'color']
    list_filter = ['intensity', 'date']
    search_fields = ['user__email']
