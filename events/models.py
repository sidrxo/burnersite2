# events/models.py
from django.db import models
from django.utils import timezone
from datetime import datetime
import warnings
from burnermanagement.firebase_config import get_firestore_client

# Suppress the Firestore filter warnings
warnings.filterwarnings("ignore", message="Detected filter using positional arguments")

class Event:
    """Event model that interfaces with Firestore"""
    
    def __init__(self, id=None, **kwargs):
        self.id = id
        self.name = kwargs.get('name', '')
        self.description = kwargs.get('description', '')
        self.venue = kwargs.get('venue', '')  # Changed from venue_name
        self.venue_id = kwargs.get('venueId', '')
        self.date = kwargs.get('date')
        self.price = kwargs.get('price', 0)
        self.max_tickets = kwargs.get('maxTickets', 0)
        self.tickets_sold = kwargs.get('ticketsSold', 0)
        self.image_url = kwargs.get('imageUrl', '')
        self.is_featured = kwargs.get('isFeatured', False)
        self.created_at = kwargs.get('createdAt')
        self.created_by = kwargs.get('createdBy', '')
        
        # Default values for fields not in your Firestore
        self.is_active = True  # Assume all events are active
        self.updated_at = None
    
    @classmethod
    def get_all_active(cls):
        """Get all events from Firestore"""
        db = get_firestore_client()
        
        if db is None:
            print("Firestore client not available")
            return []
        
        try:
            events_ref = db.collection('events')
            docs = list(events_ref.stream())
            print(f"Found {len(docs)} total events in Firestore")
            
            events = []
            now = datetime.utcnow()
            
            for doc in docs:
                data = doc.to_dict()
                print(f"Processing event: {data.get('name', 'Unknown')}")
                
                # Handle date conversion
                event_date = data.get('date')
                if event_date:
                    if hasattr(event_date, 'timestamp'):
                        # Firestore timestamp
                        event_datetime = datetime.fromtimestamp(event_date.timestamp())
                        data['date'] = event_datetime
                    elif isinstance(event_date, datetime):
                        event_datetime = event_date
                    else:
                        # Skip events without proper dates
                        print(f"Skipping event with invalid date: {event_date}")
                        continue
                    
                    # Only include future events
                    if event_datetime >= now:
                        event = cls(id=doc.id, **data)
                        events.append(event)
                        print(f"Added event: {event.name}")
                    else:
                        print(f"Skipping past event: {data.get('name')}")
                else:
                    # Include events without dates for now
                    event = cls(id=doc.id, **data)
                    events.append(event)
                    print(f"Added event without date: {event.name}")
            
            # Sort by date
            events.sort(key=lambda x: x.date if x.date else datetime.max)
            print(f"Returning {len(events)} events")
            return events
            
        except Exception as e:
            print(f"Error fetching events: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    @classmethod
    def get_by_venue(cls, venue_id):
        """Get events for a specific venue"""
        db = get_firestore_client()
        
        if db is None:
            print("Firestore client not available")
            return []
        
        try:
            events_ref = db.collection('events').where('venueId', '==', venue_id)
            docs = list(events_ref.stream())
            print(f"Found {len(docs)} events for venue {venue_id}")
            
            events = []
            now = datetime.utcnow()
            
            for doc in docs:
                data = doc.to_dict()
                
                # Handle date conversion
                event_date = data.get('date')
                if event_date and hasattr(event_date, 'timestamp'):
                    data['date'] = datetime.fromtimestamp(event_date.timestamp())
                
                event = cls(id=doc.id, **data)
                
                # Only include future events or events without dates
                if not event.date or event.date >= now:
                    events.append(event)
            
            # Sort by date
            events.sort(key=lambda x: x.date if x.date else datetime.max)
            return events
            
        except Exception as e:
            print(f"Error fetching events for venue {venue_id}: {e}")
            return []
    
    @classmethod
    def get_by_id(cls, event_id):
        """Get a specific event by ID"""
        db = get_firestore_client()
        
        if db is None:
            return None
            
        try:
            doc = db.collection('events').document(event_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                
                # Handle date conversion
                event_date = data.get('date')
                if event_date and hasattr(event_date, 'timestamp'):
                    data['date'] = datetime.fromtimestamp(event_date.timestamp())
                
                return cls(id=doc.id, **data)
        except Exception as e:
            print(f"Error fetching event {event_id}: {e}")
        
        return None
    
    @classmethod
    def get_featured(cls, limit=6):
        """Get featured events for home page"""
        events = cls.get_all_active()
        # Filter by isFeatured if available, otherwise return first few
        featured = [e for e in events if e.is_featured]
        if featured:
            return featured[:limit]
        return events[:limit]
    
    @classmethod
    def toggle_featured(cls, event_id):
        """Toggle the featured status of an event"""
        db = get_firestore_client()
        
        if db is None:
            return False
        
        try:
            doc_ref = db.collection('events').document(event_id)
            doc = doc_ref.get()
            
            if doc.exists:
                current_featured = doc.to_dict().get('isFeatured', False)
                doc_ref.update({'isFeatured': not current_featured})
                return True
            return False
        except Exception as e:
            print(f"Error toggling featured status for event {event_id}: {e}")
            return False
    
    @classmethod
    def delete_by_id(cls, event_id):
        """Delete an event by ID"""
        db = get_firestore_client()
        
        if db is None:
            return False
        
        try:
            # First, delete any tickets associated with this event
            tickets_ref = db.collection('events').document(event_id).collection('tickets')
            tickets = tickets_ref.stream()
            
            for ticket in tickets:
                ticket.reference.delete()
            
            # Then delete the event itself
            db.collection('events').document(event_id).delete()
            return True
        except Exception as e:
            print(f"Error deleting event {event_id}: {e}")
            return False
    
    @property
    def tickets_remaining(self):
        return self.max_tickets - self.tickets_sold
    
    @property
    def is_sold_out(self):
        return self.tickets_sold >= self.max_tickets
    
    @property
    def is_upcoming(self):
        if isinstance(self.date, datetime):
            return self.date > datetime.utcnow()
        return True
    
    @property
    def venue_name(self):
        """Alias for venue field to maintain compatibility"""
        return self.venue
    
    @property
    def event_status(self):
        """Get the current status of the event"""
        now = datetime.utcnow()
        if self.date and isinstance(self.date, datetime):
            if self.date < now:
                return "past"
        if self.is_sold_out:
            return "sold_out"
        return "available"
    
    def __str__(self):
        return f"Event: {self.name} (ID: {self.id})"