"""
LunaFlow Accounts Serializers
"""
from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from .models import User, UserPreferences


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for creating new user accounts."""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'password', 'password_confirm']

    def validate_email(self, value):
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        # Create default preferences
        UserPreferences.objects.create(user=user)
        return user


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login — returns JWT tokens."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(username=data['email'].lower(), password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid email or password.")
        if not user.is_active:
            raise serializers.ValidationError("This account has been deactivated.")

        refresh = RefreshToken.for_user(user)
        return {
            'user': user,
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }


class UserSerializer(serializers.ModelSerializer):
    """Read serializer for the User model."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'full_name',
                  'date_of_birth', 'created_at']
        read_only_fields = ['id', 'email', 'created_at']


class UserPreferencesSerializer(serializers.ModelSerializer):
    """Serializer for UserPreferences."""

    class Meta:
        model = UserPreferences
        fields = [
            'cycle_length_default', 'period_duration_default', 'age_range',
            'tracking_goals', 'timezone', 'last_period_date',
            'reminder_period_days_before', 'reminder_fertile_enabled',
            'reminder_daily_log_enabled', 'reminder_daily_log_time',
            'onboarding_completed',
        ]


class OnboardingSerializer(serializers.Serializer):
    """Serializer for the 4-step onboarding flow."""
    last_period_date = serializers.DateField()
    cycle_length_default = serializers.IntegerField(min_value=18, max_value=60, default=28)
    period_duration_default = serializers.IntegerField(min_value=1, max_value=10, default=5)
    age_range = serializers.ChoiceField(
        choices=['under_18', '18_25', '26_35', '36_45', 'over_45'], required=False
    )
    tracking_goals = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for changing user password."""
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError(
                {"new_password_confirm": "New passwords do not match."})
        return data
