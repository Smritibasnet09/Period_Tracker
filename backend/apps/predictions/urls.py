"""LunaFlow Predictions URLs"""
from django.urls import path
from .views import (
    PredictionLatestView, PredictionGenerateView,
    PredictionHistoryView, PredictionEvaluationView,
)

urlpatterns = [
    path('latest/', PredictionLatestView.as_view(), name='prediction-latest'),
    path('generate/', PredictionGenerateView.as_view(), name='prediction-generate'),
    path('history/', PredictionHistoryView.as_view(), name='prediction-history'),
    path('evaluation/', PredictionEvaluationView.as_view(), name='prediction-evaluation'),
]
