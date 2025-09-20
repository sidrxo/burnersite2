# events/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime
import uuid

from .models import Event
from venues.models import Venue
from .forms import EventForm
from burnermanagement.firebase_config import get_firestore_client

def events_list(request):
    """Public list view for events"""
    events = Event.get_all_active()
    return render(request, 'events/list.html', {'events': events})

def event_detail(request, event_id):
    """Public event detail page"""
    event = Event.get_by_id(event_id)
    if not event:
        raise Http404("Event does not exist")
    
    return render(request, 'events/detail.html', {'event': event})

class EventListView(LoginRequiredMixin, TemplateView):
    """Management page for events - requires authentication"""
    template_name = 'events/manage.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has permission to manage events
        if not (request.user.is_superuser or request.user.is_site_admin() or request.user.is_venue_admin() or request.user.is_sub_admin()):
            messages.error(request, "You don't have permission to access event management.")
            return redirect('core:home')
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get events based on user role
        if self.request.user.is_site_admin():
            events = Event.get_all_active()
        else:
            # Venue admin or sub-admin - filter by their venue
            if not self.request.user.venue_id:
                messages.error(self.request, "No venue assigned to your account")
                events = []
            else:
                events = Event.get_by_venue(self.request.user.venue_id)
        
        # Search functionality
        search = self.request.GET.get('search', '').strip()
        if search:
            events = [e for e in events if 
                     search.lower() in (e.name or '').lower() or
                     search.lower() in (e.venue or '').lower() or
                     search.lower() in (e.description or '').lower()]
        
        # Load venues for site admins
        venues = []
        if self.request.user.is_site_admin():
            venues = Venue.get_all_active()
        
        # Calculate stats
        total_events = len(events)
        featured_events = len([e for e in events if e.is_featured])
        sold_out_events = len([e for e in events if e.tickets_sold >= e.max_tickets])
        
        context.update({
            'events': events,
            'venues': venues,
            'search': search,
            'stats': {
                'total': total_events,
                'featured': featured_events,
                'sold_out': sold_out_events,
            }
        })
        
        return context

@login_required
def event_create(request):
    """Create new event with proper form handling"""
    if not (request.user.is_site_admin() or request.user.is_venue_admin() or request.user.is_sub_admin()):
        messages.error(request, "You don't have permission to create events")
        return redirect('events:manage')
    
    # Load venues for site admins
    venues = []
    if request.user.is_site_admin():
        venues = Venue.get_all_active()
    
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user, venues=venues)
        if form.is_valid():
            try:
                # Create event data
                event_data = {
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data['description'] or '',
                    'date': form.cleaned_data['date'],
                    'price': float(form.cleaned_data['price']),
                    'maxTickets': form.cleaned_data['max_tickets'],
                    'ticketsSold': 0,
                    'isFeatured': form.cleaned_data['is_featured'] if request.user.is_site_admin() else False,
                    'createdAt': datetime.now(),
                    'createdBy': request.user.email,
                    'imageUrl': '',
                }
                
                # Set venue information
                if request.user.is_site_admin():
                    venue_id = form.cleaned_data['venue_id']
                    venue = next((v for v in venues if v.id == venue_id), None)
                    if venue:
                        event_data['venueId'] = venue_id
                        event_data['venue'] = venue.name
                    else:
                        messages.error(request, "Selected venue not found")
                        return render(request, 'events/form.html', {'form': form, 'venues': venues, 'is_edit': False})
                else:
                    # Venue admin/sub-admin
                    if not request.user.venue_id:
                        messages.error(request, "No venue assigned to your account")
                        return redirect('events:manage')
                    
                    user_venue = request.user.get_venue()
                    event_data['venueId'] = request.user.venue_id
                    event_data['venue'] = user_venue.name if user_venue else 'Unknown Venue'
                
                # Generate unique event ID
                event_id = str(uuid.uuid4())
                
                # Save to Firestore
                db = get_firestore_client()
                if db:
                    db.collection('events').document(event_id).set(event_data)
                    messages.success(request, f"Event '{event_data['name']}' created successfully!")
                    return redirect('events:manage')
                else:
                    messages.error(request, "Failed to connect to database")
                    
            except Exception as e:
                messages.error(request, f"Error creating event: {str(e)}")
    else:
        form = EventForm(user=request.user, venues=venues)
    
    return render(request, 'events/form.html', {
        'form': form,
        'venues': venues,
        'is_edit': False
    })

@login_required  
def event_edit(request, event_id):
    """Edit existing event"""
    if not (request.user.is_site_admin() or request.user.is_venue_admin() or request.user.is_sub_admin()):
        messages.error(request, "You don't have permission to edit events")
        return redirect('events:manage')
    
    # Get the event
    event = Event.get_by_id(event_id)
    if not event:
        raise Http404("Event does not exist")
    
    # Check permissions
    if not request.user.is_site_admin():
        if request.user.venue_id != event.venue_id:
            messages.error(request, "You don't have permission to edit this event")
            return redirect('events:manage')
    
    # Load venues for site admins
    venues = []
    if request.user.is_site_admin():
        venues = Venue.get_all_active()
    
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user, venues=venues)
        if form.is_valid():
            try:
                # Update event data
                update_data = {
                    'name': form.cleaned_data['name'],
                    'description': form.cleaned_data['description'] or '',
                    'date': form.cleaned_data['date'],
                    'price': float(form.cleaned_data['price']),
                    'maxTickets': form.cleaned_data['max_tickets'],
                    'updatedAt': datetime.now(),
                }
                
                # Only site admins can update featured status
                if request.user.is_site_admin():
                    update_data['isFeatured'] = form.cleaned_data['is_featured']
                
                # Site admins can change venue
                if request.user.is_site_admin() and form.cleaned_data['venue_id']:
                    venue_id = form.cleaned_data['venue_id']
                    venue = next((v for v in venues if v.id == venue_id), None)
                    if venue:
                        update_data['venueId'] = venue_id
                        update_data['venue'] = venue.name
                
                # Update in Firestore
                db = get_firestore_client()
                if db:
                    db.collection('events').document(event_id).update(update_data)
                    messages.success(request, f"Event '{update_data['name']}' updated successfully!")
                    return redirect('events:manage')
                else:
                    messages.error(request, "Failed to connect to database")
                    
            except Exception as e:
                messages.error(request, f"Error updating event: {str(e)}")
    else:
        # Pre-populate form with existing event data
        initial_data = {
            'name': event.name,
            'description': event.description,
            'venue_id': event.venue_id,
            'date': event.date,
            'price': event.price,
            'max_tickets': event.max_tickets,
            'is_featured': event.is_featured,
        }
        form = EventForm(initial=initial_data, user=request.user, venues=venues)
    
    return render(request, 'events/form.html', {
        'form': form,
        'venues': venues,
        'event': event,
        'is_edit': True
    })

@login_required
@require_http_methods(["POST"])
def toggle_featured(request, event_id):
    """Toggle featured status (site admins only)"""
    if not request.user.is_site_admin():
        return JsonResponse({'error': 'Only site administrators can manage featured events'}, status=403)
    
    try:
        success = Event.toggle_featured(event_id)
        if success:
            return JsonResponse({'success': True, 'message': 'Event featured status updated'})
        else:
            return JsonResponse({'error': 'Event not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
@require_http_methods(["POST"])
def event_delete(request, event_id):
    """Delete event"""
    if not (request.user.is_site_admin() or request.user.is_venue_admin() or request.user.is_sub_admin()):
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    event = Event.get_by_id(event_id)
    if not event:
        return JsonResponse({'error': 'Event not found'}, status=404)
    
    # Check if user can delete this event
    if not request.user.is_site_admin():
        if request.user.venue_id != event.venue_id:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    
    try:
        success = Event.delete_by_id(event_id)
        if success:
            messages.success(request, f"Event '{event.name}' deleted successfully")
            return JsonResponse({'success': True, 'message': f"Event '{event.name}' deleted successfully"})
        else:
            return JsonResponse({'error': 'Failed to delete event'}, status=500)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)