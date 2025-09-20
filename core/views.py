# core/views.py
from django.views.generic import TemplateView
from events.models import Event
from venues.models import Venue

class HomeView(TemplateView):
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['featured_events'] = Event.get_featured(6)
        context['total_venues'] = Venue.count_active()
        context['total_events'] = len(Event.get_all_active())
        return context