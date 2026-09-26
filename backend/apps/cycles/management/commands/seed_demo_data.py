"""
LunaFlow Demo Data Seeder

Creates a test user with 12 months of realistic cycle data for development.

Usage:
    python manage.py seed_demo_data
    python manage.py seed_demo_data --email demo@lunaflow.app --password demo1234
"""
import random
from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed the database with a demo user and 12 months of realistic cycle data'

    def add_arguments(self, parser):
        parser.add_argument('--email', default='demo@lunaflow.app')
        parser.add_argument('--password', default='LunaFlow2024!')
        parser.add_argument('--first-name', default='Luna')

    def handle(self, *args, **options):
        from apps.accounts.models import UserPreferences
        from apps.cycles.models import Cycle, FlowLog
        from apps.logs.models import DailyLog, Symptom
        from apps.reminders.models import Reminder

        email = options['email']
        password = options['password']
        first_name = options['first_name']

        # Create or reset demo user
        User.objects.filter(email=email).delete()
        user = User.objects.create_user(
            email=email, password=password, first_name=first_name
        )
        self.stdout.write(f'Created user: {email} / {password}')

        # Create preferences
        prefs = UserPreferences.objects.create(
            user=user,
            cycle_length_default=28,
            period_duration_default=5,
            age_range='26_35',
            tracking_goals=['period_tracking', 'fertility_awareness'],
            onboarding_completed=True,
        )

        # Generate 12 months of cycle data (realistic variability)
        base_cycle_length = 28
        base_period_duration = 5
        today = date.today()

        # Start ~12 months ago
        start_date = today - timedelta(days=365)
        current_date = start_date

        INTENSITIES = ['spotting', 'light', 'medium', 'heavy', 'medium', 'light']
        SYMPTOMS_POOL = [
            ('cramps', 2), ('bloating', 1), ('fatigue', 2),
            ('headache', 1), ('breast_tenderness', 1), ('mood_swings', 2),
        ]
        MOODS = [3, 3, 4, 4, 2, 3, 3, 4, 2, 3]

        created_cycles = []
        cycle_num = 0

        while current_date < today - timedelta(days=14):
            cycle_num += 1

            # Add some realistic variability (±3 days from base)
            cycle_length = base_cycle_length + random.randint(-3, 3)
            period_duration = base_period_duration + random.randint(-1, 1)
            period_duration = max(2, min(7, period_duration))

            period_start = current_date
            period_end = period_start + timedelta(days=period_duration - 1)
            cycle_end = current_date + timedelta(days=cycle_length)

            # Don't extend beyond today
            if cycle_end > today:
                cycle_end = None

            cycle = Cycle.objects.create(
                user=user,
                start_date=current_date,
                end_date=cycle_end,
                period_start=period_start,
                period_end=period_end,
                is_active=(cycle_end is None),
            )
            created_cycles.append(cycle)

            # Add flow logs for period days
            for day_offset in range(period_duration):
                flow_date = period_start + timedelta(days=day_offset)
                if flow_date > today:
                    break
                intensity_idx = min(day_offset, len(INTENSITIES) - 1)
                FlowLog.objects.create(
                    user=user,
                    cycle=cycle,
                    date=flow_date,
                    intensity=INTENSITIES[intensity_idx],
                    color=random.choice(['bright_red', 'dark_red', 'brown']),
                )

            # Add daily logs for some days in the cycle
            for day_offset in range(0, cycle_length, 2):  # every other day
                log_date = current_date + timedelta(days=day_offset)
                if log_date > today:
                    break

                mood = random.choice(MOODS)
                # Lower mood during period
                if day_offset < period_duration:
                    mood = max(1, mood - 1)

                daily_log = DailyLog.objects.create(
                    user=user,
                    date=log_date,
                    mood=mood,
                    energy=random.randint(2, 5),
                    stress=random.randint(1, 4),
                    sleep_hours=random.choice([6.0, 6.5, 7.0, 7.5, 8.0, 8.5]),
                    exercise_minutes=random.choice([0, 0, 20, 30, 45, 60]),
                    appetite=random.randint(2, 5),
                )

                # Add symptoms during period and luteal phase
                if day_offset < period_duration + 5:
                    num_symptoms = random.randint(1, 3)
                    for symptom_type, default_severity in random.sample(SYMPTOMS_POOL, num_symptoms):
                        severity = max(1, min(3, default_severity + random.randint(-1, 1)))
                        Symptom.objects.get_or_create(
                            daily_log=daily_log,
                            symptom_type=symptom_type,
                            defaults={'severity': severity},
                        )

            current_date = current_date + timedelta(days=cycle_length)

        # Set the most recent cycle as active if no end_date
        last_cycle = created_cycles[-1] if created_cycles else None
        if last_cycle and last_cycle.end_date is None:
            last_cycle.is_active = True
            last_cycle.save()

        # Update preferences with last period date
        if last_cycle:
            prefs.last_period_date = last_cycle.period_start
            prefs.save()

        # Create default reminders
        Reminder.objects.create(
            user=user, reminder_type='period', days_before=2,
            time_of_day='08:00:00', is_active=True, label='Period Reminder'
        )
        Reminder.objects.create(
            user=user, reminder_type='fertile_window', days_before=1,
            time_of_day='08:00:00', is_active=True, label='Fertile Window'
        )
        Reminder.objects.create(
            user=user, reminder_type='daily_log', days_before=0,
            time_of_day='20:00:00', is_active=True, label='Daily Log'
        )

        self.stdout.write(self.style.SUCCESS(
            f'\n[SUCCESS] Demo data seeded successfully!\n'
            f'   User: {email}\n'
            f'   Password: {password}\n'
            f'   Cycles created: {len(created_cycles)}\n'
            f'   Period logs: {FlowLog.objects.filter(user=user).count()}\n'
            f'   Daily logs: {DailyLog.objects.filter(user=user).count()}\n'
        ))
