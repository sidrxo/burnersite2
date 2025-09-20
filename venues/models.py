# venues/models.py
from burnermanagement.firebase_config import get_firestore_client
from datetime import datetime
import warnings

# Suppress the Firestore filter warnings
warnings.filterwarnings("ignore", message="Detected filter using positional arguments")

class Venue:
    """Venue model that interfaces with Firestore"""
    
    def __init__(self, id=None, **kwargs):
        self.id = id
        self.name = kwargs.get('name', '')
        self.city = kwargs.get('city', '')
        self.created_at = kwargs.get('createdAt')
        self.admins = kwargs.get('admins', {})
        self.sub_admins = kwargs.get('subAdmins', {})
        
        # Set defaults for fields that don't exist in your Firestore
        self.description = ''
        self.address = ''
        self.capacity = 0
        self.image_url = ''
        self.is_active = True
        self.updated_at = None
    
    @classmethod
    def get_all_active(cls):
        """Get all venues from Firestore"""
        db = get_firestore_client()
        
        if db is None:
            return []
        
        try:
            venues_ref = db.collection('venues')
            docs = list(venues_ref.stream())
            print(f"Found {len(docs)} venues in Firestore")
            
            venues = []
            for doc in docs:
                data = doc.to_dict()
                venue = cls(id=doc.id, **data)
                venues.append(venue)
            
            # Sort by name in Python
            venues.sort(key=lambda x: x.name.lower() if x.name else '')
            return venues
            
        except Exception as e:
            print(f"Error fetching venues: {e}")
            return []
    
    @classmethod
    def get_by_id(cls, venue_id):
        """Get a specific venue by ID"""
        db = get_firestore_client()
        
        if db is None:
            return None
            
        try:
            doc = db.collection('venues').document(venue_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                return cls(id=doc.id, **data)
        except Exception as e:
            print(f"Error fetching venue {venue_id}: {e}")
        
        return None
    
    @classmethod
    def count_active(cls):
        """Count venues"""
        venues = cls.get_all_active()
        return len(venues)
    
    def get_admin_emails(self):
        """Get list of admin emails for this venue"""
        admin_emails = []
        if self.admins:
            admin_emails.extend(self.admins.keys())
        if self.sub_admins:
            admin_emails.extend(self.sub_admins.keys())
        return admin_emails
    
    def is_admin(self, email):
        """Check if email is an admin for this venue"""
        return email in self.admins if self.admins else False
    
    def is_sub_admin(self, email):
        """Check if email is a sub admin for this venue"""
        return email in self.sub_admins if self.sub_admins else False