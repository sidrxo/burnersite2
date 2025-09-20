# events/urls.py
from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Public event pages
    path('', views.events_list, name='list'),
    path('manage/', views.EventListView.as_view(), name='manage'),
    path('create/', views.event_create, name='create'),
    
    # Event management - these need to be before the generic detail pattern
    path('<str:event_id>/edit/', views.event_edit, name='edit'),
    path('<str:event_id>/toggle-featured/', views.toggle_featured, name='toggle_featured'),
    path('<str:event_id>/delete/', views.event_delete, name='delete'),
    
    # Public detail view - this should be last
    path('<str:event_id>/', views.event_detail, name='detail'),
]