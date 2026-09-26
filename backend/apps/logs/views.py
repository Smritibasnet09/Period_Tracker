"""LunaFlow Logs Views"""
from datetime import date
from django.db.models import Count, Avg
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import DailyLog, Symptom
from .serializers import DailyLogSerializer, DailyLogListSerializer, SymptomSerializer


class DailyLogViewSet(viewsets.ModelViewSet):
    """CRUD for daily health logs. User-scoped. Upserts by date."""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = DailyLog.objects.filter(user=self.request.user).prefetch_related('symptoms')
        # Optional date range filtering
        start = self.request.query_params.get('start')
        end = self.request.query_params.get('end')
        if start:
            qs = qs.filter(date__gte=start)
        if end:
            qs = qs.filter(date__lte=end)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return DailyLogListSerializer
        return DailyLogSerializer

    def get_object_by_date(self, date_str):
        return DailyLog.objects.filter(user=self.request.user, date=date_str).first()

    def retrieve(self, request, pk=None):
        """Allow retrieval by date string (YYYY-MM-DD) as pk."""
        log = self.get_object_by_date(pk) if len(str(pk)) == 10 else None
        if not log:
            try:
                log = DailyLog.objects.get(pk=pk, user=request.user)
            except DailyLog.DoesNotExist:
                return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(DailyLogSerializer(log).data)

    def create(self, request, *args, **kwargs):
        """Upsert: update if log exists for this date, else create."""
        date_str = request.data.get('date', str(date.today()))
        existing = DailyLog.objects.filter(user=request.user, date=date_str).first()

        if existing:
            serializer = DailyLogSerializer(existing, data=request.data, partial=True)
        else:
            serializer = DailyLogSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(
                serializer.data,
                status=status.HTTP_200_OK if existing else status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='today')
    def today(self, request):
        """GET /api/logs/daily/today/ — today's log."""
        log = DailyLog.objects.filter(user=request.user, date=date.today()).first()
        if not log:
            return Response({'detail': 'No log for today yet.', 'date': str(date.today())},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(DailyLogSerializer(log).data)


class SymptomPatternView(APIView):
    """GET /api/logs/symptom-patterns/ — symptom frequency analysis."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Count each symptom type across all logs
        patterns = (
            Symptom.objects.filter(daily_log__user=request.user)
            .values('symptom_type')
            .annotate(count=Count('id'), avg_severity=Avg('severity'))
            .order_by('-count')
        )

        result = []
        for p in patterns:
            result.append({
                'symptom': p['symptom_type'],
                'count': p['count'],
                'avg_severity': round(p['avg_severity'], 2) if p['avg_severity'] else None,
            })

        return Response({'symptom_patterns': result})
