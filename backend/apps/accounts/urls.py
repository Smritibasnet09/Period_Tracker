"""LunaFlow Accounts — Auth URLs"""
from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='auth-register'),
    path('login/', views.LoginView.as_view(), name='auth-login'),
    path('logout/', views.LogoutView.as_view(), name='auth-logout'),
    path('onboarding/', views.OnboardingView.as_view(), name='auth-onboarding'),
    path('change-password/', views.ChangePasswordView.as_view(), name='auth-change-password'),
]
