"""LunaFlow Logs URLs"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DailyLogViewSet, SymptomPatternView

router = DefaultRouter()
router.register(r'daily', DailyLogViewSet, basename='dailylog')

urlpatterns = [
    path('', include(router.urls)),
    path('symptom-patterns/', SymptomPatternView.as_view(), name='symptom-patterns'),
]
