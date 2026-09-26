"""LunaFlow Accounts — Profile URLs"""
from django.urls import path
from . import views

urlpatterns = [
    path('me/', views.UserProfileView.as_view(), name='profile-me'),
    path('preferences/', views.UserPreferencesView.as_view(), name='profile-preferences'),
    path('export-data/', views.ExportDataView.as_view(), name='profile-export'),
    path('delete-account/', views.DeleteAccountView.as_view(), name='profile-delete'),
]
