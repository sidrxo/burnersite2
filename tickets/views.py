# tickets/views.py
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin

class MyTicketsView(LoginRequiredMixin, ListView):
    template_name = 'tickets/my_tickets.html'
    context_object_name = 'tickets'
    
    def get_queryset(self):
        # We'll implement Ticket model next
        return []