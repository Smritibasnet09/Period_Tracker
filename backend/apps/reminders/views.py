"""LunaFlow Reminders Views"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Reminder
from .serializers import ReminderSerializer


class ReminderViewSet(viewsets.ModelViewSet):
    """CRUD for user reminders. User-scoped."""
    permission_classes = [IsAuthenticated]
    serializer_class = ReminderSerializer

    def get_queryset(self):
        return Reminder.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'], url_path='toggle')
    def toggle(self, request, pk=None):
        """POST /api/reminders/{id}/toggle/ — flip the is_active flag."""
        reminder = self.get_object()
        reminder.is_active = not reminder.is_active
        reminder.save()
        return Response(ReminderSerializer(reminder).data)

    @action(detail=False, methods=['get'], url_path='defaults')
    def defaults(self, request):
        """GET /api/reminders/defaults/ — default reminder templates."""
        return Response([
            {
                'reminder_type': 'period',
                'label': 'Period Reminder',
                'days_before': 2,
                'time_of_day': '08:00:00',
                'custom_message': "Your period is coming up in {days} days. Stay prepared!",
            },
            {
                'reminder_type': 'fertile_window',
                'label': 'Fertile Window Reminder',
                'days_before': 1,
                'time_of_day': '08:00:00',
                'custom_message': "Your fertile window is starting soon.",
            },
            {
                'reminder_type': 'daily_log',
                'label': 'Daily Log Reminder',
                'days_before': 0,
                'time_of_day': '20:00:00',
                'custom_message': "Don't forget to log how you're feeling today!",
            },
        ])
