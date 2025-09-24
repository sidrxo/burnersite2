from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.HealthCheckView.as_view(), name='health-check'),
    path('status/', views.StatusView.as_view(), name='api-status'),
]