"""
LunaFlow Accounts Views
"""
from django.contrib.auth import update_session_auth_hash
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User, UserPreferences
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    UserSerializer, UserPreferencesSerializer,
    OnboardingSerializer, ChangePasswordSerializer,
)


class RegisterView(APIView):
    """POST /api/auth/register/ — create a new user account."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'message': 'Account created successfully.',
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """POST /api/auth/login/ — authenticate and return JWT tokens."""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            user = data['user']
            # Check onboarding status
            try:
                onboarding_done = user.preferences.onboarding_completed
            except UserPreferences.DoesNotExist:
                onboarding_done = False
                UserPreferences.objects.create(user=user)

            return Response({
                'user': UserSerializer(user).data,
                'access': data['access'],
                'refresh': data['refresh'],
                'onboarding_completed': onboarding_done,
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """POST /api/auth/logout/ — blacklist the refresh token."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logged out successfully.'})
        except Exception:
            return Response({'message': 'Logged out.'})


class UserProfileView(APIView):
    """GET/PUT /api/profile/me/ — view and update user profile."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserPreferencesView(APIView):
    """GET/PUT /api/profile/preferences/ — view and update preferences."""
    permission_classes = [IsAuthenticated]

    def get_preferences(self):
        prefs, _ = UserPreferences.objects.get_or_create(user=self.request.user)
        return prefs

    def get(self, request):
        prefs = self.get_preferences()
        serializer = UserPreferencesSerializer(prefs)
        return Response(serializer.data)

    def put(self, request):
        prefs = self.get_preferences()
        serializer = UserPreferencesSerializer(prefs, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class OnboardingView(APIView):
    """POST /api/auth/onboarding/ — complete the 4-step onboarding flow."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OnboardingSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        prefs, _ = UserPreferences.objects.get_or_create(user=request.user)

        # Save preferences
        prefs.last_period_date = data['last_period_date']
        prefs.cycle_length_default = data.get('cycle_length_default', 28)
        prefs.period_duration_default = data.get('period_duration_default', 5)
        prefs.age_range = data.get('age_range', '')
        prefs.tracking_goals = data.get('tracking_goals', [])
        prefs.onboarding_completed = True
        prefs.save()

        # Create the first cycle from last_period_date
        from apps.cycles.models import Cycle
        Cycle.objects.filter(user=request.user, is_active=True).update(is_active=False)
        cycle = Cycle.objects.create(
            user=request.user,
            start_date=data['last_period_date'],
            period_start=data['last_period_date'],
            is_active=True,
        )

        return Response({
            'message': 'Onboarding complete! Welcome to LunaFlow.',
            'preferences': UserPreferencesSerializer(prefs).data,
            'first_cycle_id': cycle.id,
        })


class ChangePasswordView(APIView):
    """POST /api/auth/change-password/ — change user password."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'Incorrect password.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'message': 'Password changed successfully.'})


class ExportDataView(APIView):
    """POST /api/profile/export-data/ — export all user data as JSON."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from apps.cycles.models import Cycle, FlowLog
        from apps.logs.models import DailyLog, Symptom
        from apps.predictions.models import Prediction, PredictionEvaluation
        import json
        from django.core import serializers as django_serializers

        user = request.user

        # Gather all data
        cycles = list(Cycle.objects.filter(user=user).values())
        flow_logs = list(FlowLog.objects.filter(user=user).values())
        daily_logs = list(DailyLog.objects.filter(user=user).values())
        symptoms = list(Symptom.objects.filter(daily_log__user=user).values())
        predictions = list(Prediction.objects.filter(user=user).values())

        export_data = {
            'user': {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'date_of_birth': str(user.date_of_birth) if user.date_of_birth else None,
                'created_at': str(user.created_at),
            },
            'cycles': cycles,
            'flow_logs': flow_logs,
            'daily_logs': daily_logs,
            'symptoms': symptoms,
            'predictions': predictions,
            'exported_at': str(__import__('datetime').datetime.utcnow()),
        }

        # Serialize dates to strings
        def default_serializer(obj):
            import datetime
            if isinstance(obj, (datetime.date, datetime.datetime)):
                return obj.isoformat()
            if isinstance(obj, datetime.time):
                return obj.isoformat()
            return str(obj)

        return Response(
            json.loads(json.dumps(export_data, default=default_serializer)),
            status=status.HTTP_200_OK,
        )


class DeleteAccountView(APIView):
    """DELETE /api/profile/delete-account/ — permanently delete user account and all data."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response(
                {'error': 'Please provide your current password to confirm account deletion.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        email = request.user.email
        request.user.delete()  # Cascades to all related data
        return Response(
            {'message': f'Account for {email} has been permanently deleted.'},
            status=status.HTTP_200_OK,
        )
