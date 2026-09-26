"""
LunaFlow Cycles Views

CycleViewSet: Full CRUD + calendar data + end cycle action.
FlowLogViewSet: Daily flow logs.
InsightsView: Cycle statistics and personalized insights.
"""
import statistics
from datetime import date, timedelta
from django.db.models import Q, Avg
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Cycle, FlowLog
from .serializers import (
    CycleSerializer, CycleCreateSerializer, CycleUpdateSerializer,
    FlowLogSerializer,
)


class CycleViewSet(viewsets.ModelViewSet):
    """CRUD for menstrual cycles. All data is user-scoped."""
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Cycle.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        if self.action == 'create':
            return CycleCreateSerializer
        if self.action in ['update', 'partial_update']:
            return CycleUpdateSerializer
        return CycleSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['request'] = self.request
        return ctx

    @action(detail=False, methods=['get'], url_path='current')
    def current(self, request):
        """GET /api/cycles/current/ — returns the active (current) cycle."""
        cycle = Cycle.objects.filter(user=request.user, is_active=True).first()
        if not cycle:
            return Response({'detail': 'No active cycle found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(CycleSerializer(cycle).data)

    @action(detail=True, methods=['post'], url_path='end')
    def end_cycle(self, request, pk=None):
        """POST /api/cycles/{id}/end/ — manually end an active cycle."""
        cycle = self.get_object()
        end_date = request.data.get('end_date') or str(date.today())
        cycle.end_date = end_date
        cycle.is_active = False
        cycle.save()
        return Response(CycleSerializer(cycle).data)

    @action(detail=False, methods=['get'], url_path='calendar')
    def calendar_data(self, request):
        """GET /api/cycles/calendar/?month=YYYY-MM — calendar data for a month."""
        month_str = request.query_params.get('month', str(date.today())[:7])
        try:
            year, month = map(int, month_str.split('-'))
            from calendar import monthrange
            _, last_day = monthrange(year, month)
            month_start = date(year, month, 1)
            month_end = date(year, month, last_day)
        except (ValueError, AttributeError):
            return Response({'error': 'Invalid month format. Use YYYY-MM.'}, status=400)

        # Get cycles that overlap with this month
        cycles = Cycle.objects.filter(
            user=request.user,
            start_date__lte=month_end,
        ).filter(
            Q(end_date__gte=month_start) | Q(end_date__isnull=True)
        )

        # Build day-by-day data
        days = {}
        for cycle in cycles:
            # Mark period days
            period_start = cycle.period_start
            period_end = cycle.period_end or (period_start + timedelta(days=4))
            d = period_start
            while d <= period_end and d <= month_end:
                if d >= month_start:
                    days[str(d)] = {**days.get(str(d), {}), 'is_period': True, 'cycle_id': cycle.id}
                d += timedelta(days=1)

        # Get latest prediction to show predicted days
        from apps.predictions.models import Prediction
        prediction = Prediction.objects.filter(user=request.user, is_latest=True).first()
        if prediction and prediction.predicted_start_date:
            pred_start = prediction.predicted_start_date
            pred_end = prediction.predicted_end_date
            d = pred_start
            while d <= pred_end and d <= month_end:
                if d >= month_start:
                    existing = days.get(str(d), {})
                    if not existing.get('is_period'):
                        days[str(d)] = {**existing, 'is_predicted_period': True}
                d += timedelta(days=1)

            # Fertile window
            if prediction.fertile_window_start:
                d = prediction.fertile_window_start
                while d <= prediction.fertile_window_end and d <= month_end:
                    if d >= month_start:
                        days[str(d)] = {**days.get(str(d), {}), 'is_fertile': True}
                    d += timedelta(days=1)

            # Ovulation
            if prediction.estimated_ovulation:
                ov = str(prediction.estimated_ovulation)
                if ov not in days:
                    days[ov] = {}
                days[ov]['is_ovulation'] = True

        # Mark days with symptoms logged
        from apps.logs.models import DailyLog
        log_dates = DailyLog.objects.filter(
            user=request.user,
            date__gte=month_start,
            date__lte=month_end,
        ).values_list('date', flat=True)
        for d in log_dates:
            key = str(d)
            days[key] = {**days.get(key, {}), 'has_log': True}

        return Response({
            'month': month_str,
            'days': days,
            'prediction': {
                'predicted_start': str(prediction.predicted_start_date) if prediction else None,
                'predicted_end': str(prediction.predicted_end_date) if prediction else None,
                'fertile_start': str(prediction.fertile_window_start) if prediction and prediction.fertile_window_start else None,
                'fertile_end': str(prediction.fertile_window_end) if prediction and prediction.fertile_window_end else None,
                'ovulation': str(prediction.estimated_ovulation) if prediction and prediction.estimated_ovulation else None,
            } if prediction else None,
        })



class FlowLogViewSet(viewsets.ModelViewSet):
    """CRUD for daily flow logs. User-scoped."""
    permission_classes = [IsAuthenticated]
    serializer_class = FlowLogSerializer

    def get_queryset(self):
        return FlowLog.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class InsightsView(APIView):
    """GET /api/insights/cycle-stats/ — returns statistical insights from cycle history."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        # Only use completed cycles (with a cycle_length)
        cycles = list(
            Cycle.objects.filter(user=user, cycle_length__isnull=False)
            .order_by('start_date')
            .values('id', 'start_date', 'end_date', 'cycle_length',
                    'period_start', 'period_end', 'period_duration')
        )

        if not cycles:
            return Response({
                'avg_cycle_length': None,
                'median_cycle_length': None,
                'min_cycle_length': None,
                'max_cycle_length': None,
                'std_cycle_length': None,
                'avg_period_duration': None,
                'cycle_count': 0,
                'regularity_score': None,
                'recent_trend': None,
                'personalized_insights': [
                    "Start logging your periods to see personalized insights here!"
                ],
                'anomaly_detected': False,
                'anomaly_message': None,
                'cycle_history': [],
            })

        lengths = [c['cycle_length'] for c in cycles if c['cycle_length']]
        durations = [c['period_duration'] for c in cycles if c['period_duration']]

        avg_length = round(statistics.mean(lengths), 1) if lengths else None
        median_length = round(statistics.median(lengths), 1) if lengths else None
        min_length = min(lengths) if lengths else None
        max_length = max(lengths) if lengths else None
        std_length = round(statistics.stdev(lengths), 2) if len(lengths) > 1 else 0
        avg_duration = round(statistics.mean(durations), 1) if durations else None

        # Regularity score: 100 * (1 / (1 + std_dev)), 0-100
        regularity_score = None
        if std_length is not None:
            regularity_score = round(100 * (1 / (1 + std_length)), 1)

        # Trend: slope of last 5 cycle lengths
        recent_trend = 'stable'
        if len(lengths) >= 3:
            recent = lengths[-5:]
            if len(recent) >= 2:
                slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
                if slope > 0.5:
                    recent_trend = 'getting_longer'
                elif slope < -0.5:
                    recent_trend = 'getting_shorter'
                else:
                    recent_trend = 'stable'

        # Anomaly detection (most recent cycle vs historical average)
        anomaly_detected = False
        anomaly_message = None
        if len(lengths) >= 3 and std_length and std_length > 0:
            latest_length = lengths[-1]
            z_score = abs(latest_length - avg_length) / std_length
            if z_score > 2:
                anomaly_detected = True
                if latest_length > avg_length:
                    anomaly_message = (
                        f"Your most recent cycle ({latest_length} days) was notably longer "
                        f"than your usual average ({avg_length} days). "
                        "This can be caused by stress, travel, illness, or other factors. "
                        "If you're concerned, speak with a healthcare provider."
                    )
                else:
                    anomaly_message = (
                        f"Your most recent cycle ({latest_length} days) was notably shorter "
                        f"than your usual average ({avg_length} days). "
                        "This can be caused by stress, travel, illness, or other factors. "
                        "If you're concerned, speak with a healthcare provider."
                    )

        # Personalized insights
        insights = []
        if len(lengths) >= 3:
            last3_avg = round(statistics.mean(lengths[-3:]), 1)
            if last3_avg > avg_length + 1:
                insights.append(
                    f"Your last 3 cycles averaged {last3_avg} days — slightly longer than your overall average of {avg_length} days."
                )
            elif last3_avg < avg_length - 1:
                insights.append(
                    f"Your last 3 cycles averaged {last3_avg} days — slightly shorter than your overall average of {avg_length} days."
                )
            else:
                insights.append(f"Your cycle length has been very consistent lately (avg {last3_avg} days).")

        if regularity_score and regularity_score >= 70:
            insights.append("Your cycles are quite regular — great for planning ahead!")
        elif regularity_score and regularity_score < 40:
            insights.append("Your cycle length varies quite a bit. This is common and can be influenced by stress, sleep, and lifestyle.")

        if avg_duration:
            insights.append(f"Your average period lasts {avg_duration} days.")

        if not insights:
            insights.append("Keep logging your cycles to unlock personalized insights!")

        # Full cycle history
        all_cycles_qs = Cycle.objects.filter(user=user).order_by('-start_date')[:12]
        from .serializers import CycleSerializer
        cycle_history = CycleSerializer(all_cycles_qs, many=True).data

        return Response({
            'avg_cycle_length': avg_length,
            'median_cycle_length': median_length,
            'min_cycle_length': min_length,
            'max_cycle_length': max_length,
            'std_cycle_length': std_length,
            'avg_period_duration': avg_duration,
            'cycle_count': len(cycles),
            'regularity_score': regularity_score,
            'recent_trend': recent_trend,
            'personalized_insights': insights,
            'anomaly_detected': anomaly_detected,
            'anomaly_message': anomaly_message,
            'cycle_history': cycle_history,
        })
