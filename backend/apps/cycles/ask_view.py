"""
LunaFlow AI Assistant ("Ask Your Cycle") Service & API View

Answers personalized questions using the user's actual database cycle records,
as well as general educational questions with safe non-diagnostic advice.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from datetime import date, timedelta
import statistics

from apps.cycles.models import Cycle
from apps.predictions.models import Prediction
from apps.logs.models import DailyLog, Symptom


class AskCycleAssistantView(APIView):
    """
    POST /api/insights/ask/
    Body: {"question": "When is my next period?"}
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        question_raw = request.data.get('question', '').strip()
        if not question_raw:
            return Response({'error': 'Please provide a question.'}, status=status.HTTP_400_BAD_REQUEST)

        q = question_raw.lower()

        # 1. Fetch user context
        completed_cycles = list(Cycle.objects.filter(user=user, cycle_length__isnull=False).order_by('start_date'))
        active_cycle = Cycle.objects.filter(user=user, is_active=True).first()
        latest_pred = Prediction.objects.filter(user=user, is_latest=True).first()
        recent_logs = list(DailyLog.objects.filter(user=user).order_by('-date')[:14])
        
        lengths = [c.cycle_length for c in completed_cycles if c.cycle_length]
        avg_length = round(statistics.mean(lengths), 1) if lengths else 28
        
        # Calculate current cycle day
        cycle_day = 1
        if active_cycle and active_cycle.start_date:
            cycle_day = max(1, (date.today() - active_cycle.start_date).days + 1)
        elif completed_cycles:
            cycle_day = max(1, (date.today() - completed_cycles[-1].start_date).days + 1)

        # Estimate phase
        ovulation_day = max(12, int(avg_length) - 14)
        if cycle_day <= 5:
            current_phase = "Menstrual Phase"
            phase_desc = "Your body is shedding the uterine lining. Rest and hydration are especially beneficial right now."
        elif cycle_day < ovulation_day - 3:
            current_phase = "Follicular Phase"
            phase_desc = "Estrogen is gradually increasing, often bringing rising energy, focus, and creativity."
        elif cycle_day <= ovulation_day + 1:
            current_phase = "Ovulatory Phase"
            phase_desc = "This is your peak fertility window where an egg is released."
        else:
            current_phase = "Luteal Phase"
            phase_desc = "Progesterone is the dominant hormone. You may experience PMS symptoms or a natural shift toward rest."

        response_type = "personalized"
        answer = ""
        context_used = []
        follow_up = []

        # 2. Intent matching with user data grounding (supports English and Romanized Nepali queries)
        
        # Question: When is next period? ('kahile hunchha', 'next period', 'aune date')
        if any(k in q for k in ['next period', 'when will my period start', 'when is my period', 'next cycle', 'kahile hunchha', 'kahile aaucha', 'aune date', 'next date']):
            if latest_pred:
                pred_start = latest_pred.predicted_start_date.strftime('%B %d')
                pred_end = latest_pred.predicted_end_date.strftime('%B %d')
                uncertainty = latest_pred.uncertainty_days
                answer = (
                    f"Based on your recent cycle history, your next period is estimated around {pred_start}–{pred_end} "
                    f"(with a variability window of ±{uncertainty} days).\n\n"
                    f"Your recent cycles have averaged around {avg_length} days. Because cycle lengths naturally fluctuate, "
                    f"this is provided as a personalized range rather than an exact fixed date."
                )
                context_used = [f"Average cycle: {avg_length} days", f"Model: {latest_pred.model_used}", f"Active cycle day: Day {cycle_day}"]
            else:
                answer = f"Based on your typical cycle settings, your next period is expected in about {max(1, int(avg_length) - cycle_day)} days. As you log more dates, this prediction will become more personalized."
                context_used = [f"Cycle Day: {cycle_day}"]
            follow_up = ["What phase am I currently in?", "When is my fertile window?"]

        # Question: Cycle day ('kun din', 'katina din', 'cycle day')
        elif any(k in q for k in ['cycle day', 'what day am i on', 'current day', 'katina din', 'kun din']):
            answer = (
                f"You are currently on Cycle Day {cycle_day}.\n\n"
                f"Cycle Day 1 represents the first day of your last recorded period. "
                f"Your typical cycle length has averaged {avg_length} days."
            )
            context_used = [f"Cycle Day {cycle_day}", f"Last period start: {active_cycle.start_date if active_cycle else 'Recorded'}"]
            follow_up = ["What phase am I in?", "When might I ovulate?"]

        # Question: Current phase ('kun phase', 'phase')
        elif any(k in q for k in ['what phase', 'current phase', 'phase am i', 'kun phase', 'phase k ho']):
            answer = (
                f"You're currently around Cycle Day {cycle_day}. Based on your recorded history, you are likely in your {current_phase}.\n\n"
                f"{phase_desc}"
            )
            context_used = [f"Cycle Day {cycle_day}", f"Phase: {current_phase}"]
            follow_up = ["When is my next period?", "Why am I having cramps?"]

        # Question: Ovulation / Fertile window
        elif any(k in q for k in ['ovulat', 'fertile', 'fertile window', 'chance of pregnancy']):
            if latest_pred and latest_pred.fertile_window_start and latest_pred.fertile_window_end:
                f_start = latest_pred.fertile_window_start.strftime('%B %d')
                f_end = latest_pred.fertile_window_end.strftime('%B %d')
                ov_str = latest_pred.estimated_ovulation.strftime('%B %d') if latest_pred.estimated_ovulation else 'mid-cycle'
                answer = (
                    f"Your estimated fertile window is from {f_start} to {f_end}, with estimated ovulation around {ov_str}.\n\n"
                    f"The fertile window generally encompasses the 5 days before ovulation plus ovulation day itself. "
                    f"Please keep in mind that ovulation estimates are statistical approximations and should not be used as contraception."
                )
                context_used = [f"Fertile window: {f_start} - {f_end}", f"Ovulation: ~{ov_str}"]
            else:
                answer = (
                    f"In an average {int(avg_length)}-day cycle, ovulation usually occurs around Day {ovulation_day} (approximately 14 days before your next period). "
                    f"Your fertile window typically spans 5 days prior to ovulation up to the day of ovulation."
                )
            follow_up = ["What happens during ovulation?", "When is my next period?"]

        # Question: Symptoms / Cramps
        elif any(k in q for k in ['cramp', 'symptom', 'pain', 'bloat', 'headache', 'mood']):
            # Query user symptoms
            symptoms = list(Symptom.objects.filter(daily_log__user=user).values('symptom_type'))
            symp_counts = {}
            for s in symptoms:
                st = s['symptom_type'].replace('_', ' ')
                symp_counts[st] = symp_counts.get(st, 0) + 1
            
            top_symps = sorted(symp_counts.items(), key=lambda x: x[1], reverse=True)[:3]
            top_str = ", ".join([f"{name} ({count} times)" for name, count in top_symps]) if top_symps else "mild fatigue and cramps"

            if 'cramp' in q:
                answer = (
                    f"Cramps are often tied to prostaglandins released during your menstrual cycle, causing uterine muscles to contract. "
                    f"In your logs, cramps are among your recorded patterns.\n\n"
                    f"You're currently in your {current_phase} (Day {cycle_day}). Cramps can occur right before or during menstruation, and occasionally mild twinges happen around ovulation.\n\n"
                    f"Helpful supportive habits include warm compresses, staying hydrated, magnesium-rich foods, and gentle walking. If pain is severe or debilitating, consult a doctor."
                )
            else:
                answer = (
                    f"Looking at your tracked logs, your most commonly reported symptoms are: {top_str}.\n\n"
                    f"Tracking your symptoms helps you identify whether things like bloating or mood swings consistently align with your luteal or menstrual phases."
                )
            context_used = [f"Current phase: {current_phase}", f"Top logged symptoms: {top_str}"]
            follow_up = ["Was my last cycle normal for me?", "What phase am I in?"]

        # Question: Cycle length / History / Was last cycle normal?
        elif any(k in q for k in ['how long', 'cycle length', 'normal for me', 'last cycle', 'average']):
            if len(completed_cycles) >= 1:
                last_len = completed_cycles[-1].cycle_length or 28
                diff = last_len - avg_length
                diff_text = "consistent with" if abs(diff) <= 1 else ("slightly longer than" if diff > 0 else "slightly shorter than")
                
                answer = (
                    f"Your recorded cycles have an average length of {avg_length} days (ranging between {min(lengths)} and {max(lengths)} days).\n\n"
                    f"Your last recorded cycle was {last_len} days, which is {diff_text} your typical pattern.\n\n"
                    f"A variation of 2 to 4 days between cycles is completely normal and can be influenced by stress, sleep quality, travel, or activity level."
                )
                context_used = [f"Average: {avg_length} days", f"Last cycle: {last_len} days", f"Cycles recorded: {len(completed_cycles)}"]
            else:
                answer = f"Your default cycle length is set to {avg_length} days. Once you complete your first couple of cycles, we will show your personalized historical variation here!"
            follow_up = ["Why did my prediction change?", "When is my next period?"]

        # Question: Why did prediction change?
        elif any(k in q for k in ['why did my prediction change', 'prediction different', 'prediction change']):
            answer = (
                f"Your cycle prediction updates dynamically whenever you log new period dates, cycle lengths, or daily symptoms.\n\n"
                f"Our ML prediction engine analyzes your rolling average, recent trend, and cycle variability. "
                f"If your last cycle was slightly shorter or longer than usual, the model adjusts the predicted window to reflect your body's recent rhythm."
            )
            context_used = [f"Model: {latest_pred.model_used if latest_pred else 'Statistical'}", f"Variability: ±{latest_pred.uncertainty_days if latest_pred else 2} days"]
            follow_up = ["When is my next period?", "Was my last cycle normal for me?"]

        # Educational: What is ovulation / luteal / follicular?
        elif 'what is ovulation' in q:
            response_type = "educational"
            answer = (
                "Ovulation is the release of a mature egg from an ovary into the fallopian tube, where it can potentially be fertilized. "
                "It typically happens once per cycle, about 12 to 14 days before your next period begins. "
                "Because sperm can live for up to 5 days, your fertile window includes the days leading up to ovulation."
            )
            follow_up = ["When is my fertile window?", "What happens during the luteal phase?"]

        elif 'luteal phase' in q:
            response_type = "educational"
            answer = (
                "The luteal phase begins right after ovulation and lasts until your period starts (typically 12–14 days). "
                "During this time, the corpus luteum produces progesterone to support a potential pregnancy. "
                "If fertilization doesn't occur, progesterone drops, triggering menstruation. This drop is also when PMS symptoms commonly appear."
            )
            follow_up = ["What phase am I in?", "Why am I having cramps?"]

        else:
            # Fallback helpful response combining user context
            answer = (
                f"Here is a summary of your current cycle status:\n\n"
                f"• Current Cycle: Day {cycle_day} ({current_phase})\n"
                f"• Average Cycle Length: {avg_length} days\n"
                f"• Next Estimated Period: {latest_pred.predicted_start_date.strftime('%B %d') if latest_pred else 'Updating...'}\n\n"
                f"Feel free to ask specific questions like 'When is my next period?', 'What phase am I in?', or 'When might I ovulate?'"
            )
            context_used = [f"Cycle Day {cycle_day}", f"Phase: {current_phase}"]
            follow_up = ["When is my next period?", "What phase am I in?", "When is my fertile window?"]

        return Response({
            'question': question_raw,
            'answer': answer,
            'response_type': response_type,
            'context_used': context_used,
            'suggested_follow_ups': follow_up,
            'disclaimer': "This information is for tracking and educational awareness, not a medical diagnosis. Consult a healthcare provider for medical advice."
        })
