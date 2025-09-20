# tickets/urls.py
from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    path('my-tickets/', views.MyTicketsView.as_view(), name='my_tickets'),
]