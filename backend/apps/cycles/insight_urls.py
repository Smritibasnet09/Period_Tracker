from django.urls import path
from .views import InsightsView
from .ask_view import AskCycleAssistantView

urlpatterns = [
    path('cycle-stats/', InsightsView.as_view(), name='cycle-stats'),
    path('ask/', AskCycleAssistantView.as_view(), name='ask-cycle'),
]
