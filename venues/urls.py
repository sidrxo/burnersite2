# venues/urls.py
from django.urls import path
from . import views

app_name = 'venues'

urlpatterns = [
    path('', views.VenueListView.as_view(), name='list'),
    path('dashboard/', views.VenueDashboardView.as_view(), name='dashboard'),
    path('<str:pk>/', views.VenueDetailView.as_view(), name='detail'),  # This should be last
]