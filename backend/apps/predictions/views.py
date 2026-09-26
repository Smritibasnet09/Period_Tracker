"""
LunaFlow Predictions Views

Handles generating predictions (via ML service or built-in fallback),
storing them, and evaluating past predictions against actual data.
"""
import statistics
import requests
from datetime import date, timedelta
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from .models import Prediction, PredictionEvaluation
from .serializers import PredictionSerializer, PredictionEvaluationSerializer
from apps.cycles.models import Cycle


def _compute_ovulation(period_start: date, cycle_length: int) -> date:
    """Ovulation ~14 days before end of cycle."""
    return period_start + timedelta(days=cycle_length - 14)


def _compute_fertile_window(ovulation_date: date):
    """Fertile window: 5 days before ovulation to 1 day after."""
    return ovulation_date - timedelta(days=5), ovulation_date + timedelta(days=1)


def _compute_uncertainty(cycle_lengths: list) -> int:
    """Uncertainty = max(1, min(7, round(std_dev * 1.5)))"""
    if len(cycle_lengths) < 2:
        return 4
    std = statistics.stdev(cycle_lengths)
    return max(1, min(7, round(std * 1.5)))


def _statistical_prediction(cycles: list, default_length: int) -> dict:
    """
    Built-in statistical predictor (fallback when ML service is unavailable).

    Tier 0 (0-1 cycles): use default_length
    Tier 1 (2-3 cycles): weighted average (recent = 3x, previous = 2x, rest = 1x)
    Tier 2 (4+ cycles): rolling average of last 5
    """
    completed = [c for c in cycles if c.cycle_length is not None]
    n = len(completed)
    lengths = [c.cycle_length for c in completed]

    if n == 0:
        predicted_length = default_length
        model = 'baseline'
        confidence = 'low'
        uncertainty = 4
        factors = ['typical_cycle_length']
        explanation = {
            'text': (
                "Prediction based on your typical cycle length setting. "
                "Log more periods for personalized predictions."
            ),
            'factors': ['Typical cycle length (default)'],
            'trend_message': '',
            'confidence_message': 'Confidence: Low — not enough data yet.',
            'disclaimer': 'This is an estimate, not a medical diagnosis.',
        }
        cycles_used = 0

    elif n <= 3:
        if n == 1:
            predicted_length = lengths[0]
        elif n == 2:
            predicted_length = round((lengths[-1] * 3 + lengths[-2] * 2) / 5)
        else:
            predicted_length = round((lengths[-1] * 3 + lengths[-2] * 2 + lengths[-3]) / 6)
        model = 'statistical'
        confidence = 'low' if n == 1 else 'medium'
        uncertainty = _compute_uncertainty(lengths)
        factors = ['previous_cycle_lengths', 'weighted_average']
        explanation = {
            'text': (
                f"Based on your {n} recorded cycle{'s' if n > 1 else ''}, "
                f"your average is {round(statistics.mean(lengths), 1)} days. "
                "Log more cycles for ML-powered predictions."
            ),
            'factors': [f'Last {n} cycle length(s)'],
            'trend_message': '',
            'confidence_message': f'Confidence: {"Medium" if n >= 2 else "Low"} — {n} cycle(s) recorded.',
            'disclaimer': 'This is an estimate, not a medical diagnosis.',
        }
        cycles_used = n

    else:
        recent = lengths[-5:]
        predicted_length = round(statistics.mean(recent))
        model = 'statistical'
        confidence = 'medium'
        uncertainty = _compute_uncertainty(lengths)

        # Compute trend
        if len(recent) >= 3:
            slope = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
            if slope > 0.5:
                trend_msg = f"Your last {len(recent)} cycles have been getting slightly longer."
            elif slope < -0.5:
                trend_msg = f"Your last {len(recent)} cycles have been getting slightly shorter."
            else:
                trend_msg = "Your cycle length has been stable lately."
        else:
            trend_msg = ""

        overall_avg = round(statistics.mean(lengths), 1)
        explanation = {
            'text': (
                f"Your prediction is mainly based on your last {min(n, 5)} cycle lengths, "
                f"with an average of {overall_avg} days. "
                "Connect the ML service for advanced AI predictions."
            ),
            'factors': [f'Rolling average of last {min(n, 5)} cycles', 'Cycle variability'],
            'trend_message': trend_msg,
            'confidence_message': f'Confidence: Medium — {n} cycles recorded.',
            'disclaimer': 'This is an estimate, not a medical diagnosis.',
        }
        cycles_used = min(n, 5)
        factors = ['rolling_average_5', 'cycle_variability', 'prev_cycle_length']

    # Compute predicted dates from the last cycle's start
    if completed:
        last_period_start = completed[-1].period_start
    else:
        # Fall back to user preference or today
        from apps.accounts.models import UserPreferences
        return {
            'predicted_length': predicted_length,
            'last_period_start': date.today() - timedelta(days=14),
            'model': model, 'confidence': confidence, 'uncertainty': uncertainty,
            'factors': factors, 'explanation': explanation, 'cycles_used': cycles_used,
        }

    return {
        'predicted_length': predicted_length,
        'last_period_start': last_period_start,
        'model': model, 'confidence': confidence, 'uncertainty': uncertainty,
        'factors': factors, 'explanation': explanation, 'cycles_used': cycles_used,
    }


def _call_ml_service(user, cycles, prefs) -> dict | None:
    """Try to call the FastAPI ML service. Returns response dict or None on failure."""
    try:
        from apps.logs.models import DailyLog
        ml_url = getattr(settings, 'ML_SERVICE_URL', 'http://localhost:8001')
        logs = DailyLog.objects.filter(user=user).order_by('-date')[:30]
        daily_logs_payload = [
            {
                'date': str(log.date),
                'mood': float(log.mood) if log.mood is not None else None,
                'energy': float(log.energy) if log.energy is not None else None,
                'stress': float(log.stress) if log.stress is not None else None,
                'sleep_hours': float(log.sleep_hours) if log.sleep_hours is not None else None,
                'exercise_minutes': float(log.exercise_minutes) if log.exercise_minutes is not None else None,
            }
            for log in logs
        ]
        payload = {
            'user_id': user.id,
            'cycle_length_default': prefs.cycle_length_default,
            'period_duration_default': prefs.period_duration_default,
            'cycles': [
                {
                    'cycle_id': c.id,
                    'start_date': str(c.start_date),
                    'end_date': str(c.end_date) if c.end_date else None,
                    'cycle_length': c.cycle_length,
                    'period_start': str(c.period_start),
                    'period_end': str(c.period_end) if c.period_end else None,
                    'period_duration': c.period_duration,
                }
                for c in cycles
            ],
            'daily_logs': daily_logs_payload,
        }
        response = requests.post(f"{ml_url}/predict", json=payload, timeout=5)
        if response.status_code == 200:
            return response.json()
    except Exception:
        pass
    return None


class PredictionLatestView(APIView):
    """GET /api/predictions/latest/ — returns the most recent prediction."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pred = Prediction.objects.filter(user=request.user, is_latest=True).first()
        if not pred:
            return Response({'detail': 'No prediction yet. Use /generate/ to create one.'},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(PredictionSerializer(pred).data)


class PredictionGenerateView(APIView):
    """POST /api/predictions/generate/ — generate a new prediction."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        cycles = list(Cycle.objects.filter(user=user).order_by('start_date'))

        try:
            prefs = user.preferences
        except Exception:
            from apps.accounts.models import UserPreferences
            prefs, _ = UserPreferences.objects.get_or_create(user=user)

        # Try ML service first, fall back to statistical
        ml_response = _call_ml_service(user, cycles, prefs)

        if ml_response:
            predicted_start = date.fromisoformat(ml_response['predicted_start_date'])
            predicted_length = ml_response['predicted_cycle_length']
            uncertainty = ml_response['uncertainty_days']
            model = ml_response['model_used']
            confidence = ml_response['confidence_level']
            explanation = ml_response.get('explanation', {})
            factors = ml_response.get('factors_used', [])
            cycles_used = ml_response.get('cycles_used_count', 0)
            fertile_start = date.fromisoformat(ml_response['fertile_window_start'])
            fertile_end = date.fromisoformat(ml_response['fertile_window_end'])
            ovulation = date.fromisoformat(ml_response['estimated_ovulation'])
        else:
            # Use built-in statistical predictor
            result = _statistical_prediction(cycles, prefs.cycle_length_default)
            last_period_start = result['last_period_start']
            predicted_length = result['predicted_length']
            uncertainty = result['uncertainty']
            model = result['model']
            confidence = result['confidence']
            explanation = result['explanation']
            factors = result['factors']
            cycles_used = result['cycles_used']

            predicted_start = last_period_start + timedelta(days=predicted_length)
            ovulation = _compute_ovulation(predicted_start, predicted_length)
            fertile_start, fertile_end = _compute_fertile_window(ovulation)

        predicted_end = predicted_start + timedelta(days=prefs.period_duration_default - 1)

        # Mark old predictions as not latest
        Prediction.objects.filter(user=user, is_latest=True).update(is_latest=False)

        # Create new prediction
        pred = Prediction.objects.create(
            user=user,
            predicted_start_date=predicted_start,
            predicted_end_date=predicted_end,
            predicted_cycle_length=predicted_length,
            uncertainty_days=uncertainty,
            model_used=model,
            confidence_level=confidence,
            explanation=explanation,
            factors_used=factors,
            cycles_used_count=cycles_used,
            fertile_window_start=fertile_start,
            fertile_window_end=fertile_end,
            estimated_ovulation=ovulation,
            is_latest=True,
        )

        # Auto-evaluate previous predictions
        self._auto_evaluate(user, cycles)

        return Response(PredictionSerializer(pred).data, status=status.HTTP_201_CREATED)

    def _auto_evaluate(self, user, cycles):
        """Check if any pending predictions can now be evaluated against actual cycle data."""
        from apps.predictions.models import Prediction
        unevaluated = Prediction.objects.filter(
            user=user, is_latest=False
        ).exclude(evaluation__isnull=False)

        for pred in unevaluated:
            # Find a cycle that started close to the predicted date
            matching_cycle = Cycle.objects.filter(
                user=user,
                start_date__gte=pred.predicted_start_date - timedelta(days=10),
                start_date__lte=pred.predicted_start_date + timedelta(days=10),
            ).first()

            if matching_cycle:
                PredictionEvaluation.objects.get_or_create(
                    prediction=pred,
                    defaults={
                        'predicted_start': pred.predicted_start_date,
                        'actual_start': matching_cycle.start_date,
                        'actual_cycle': matching_cycle,
                    }
                )


class PredictionHistoryView(APIView):
    """GET /api/predictions/history/ — last 10 predictions."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        preds = Prediction.objects.filter(user=request.user)[:10]
        return Response(PredictionSerializer(preds, many=True).data)


class PredictionEvaluationView(APIView):
    """GET /api/predictions/evaluation/ — predicted vs actual comparison."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        evals = PredictionEvaluation.objects.filter(
            prediction__user=request.user
        ).select_related('prediction')
        serializer = PredictionEvaluationSerializer(evals, many=True)

        # Also compute aggregate metrics
        all_diffs = [e.difference_days for e in evals if e.difference_days is not None]
        accurate = [e for e in evals if e.was_accurate]

        metrics = {
            'total_evaluated': len(evals),
            'mae_days': round(statistics.mean([abs(d) for d in all_diffs]), 2) if all_diffs else None,
            'accuracy_within_2_days_pct': round(
                len(accurate) / len(evals) * 100, 1
            ) if evals else None,
            'evaluations': serializer.data,
        }
        return Response(metrics)
