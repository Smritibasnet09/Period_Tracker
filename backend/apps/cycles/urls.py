"""LunaFlow Cycles URLs"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CycleViewSet, FlowLogViewSet

router = DefaultRouter()
router.register(r'flow', FlowLogViewSet, basename='flowlog')
router.register(r'', CycleViewSet, basename='cycle')

urlpatterns = router.urls
