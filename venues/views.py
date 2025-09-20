# venues/views.py
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from .models import Venue

class VenueListView(TemplateView):
    template_name = 'venues/list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['venues'] = Venue.get_all_active()
        return context

class VenueDetailView(TemplateView):
    template_name = 'venues/detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        venue_id = kwargs.get('pk')
        venue = Venue.get_by_id(venue_id)
        
        if not venue:
            from django.http import Http404
            raise Http404("Venue does not exist")
        
        context['venue'] = venue
        return context

class VenueDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'venues/dashboard.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has venue management permissions
        if not (request.user.is_site_admin() or request.user.is_venue_admin() or request.user.is_sub_admin()):
            messages.error(request, "You don't have permission to access the venue dashboard.")
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)