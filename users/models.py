# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('scanner', 'Scanner'),
        ('subAdmin', 'Sub Admin'),
        ('venueAdmin', 'Venue Admin'),
        ('siteAdmin', 'Site Admin'),
    ]
    
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    venue_id = models.CharField(max_length=100, blank=True)  # Store Firestore venue ID instead
    created_at = models.DateTimeField(auto_now_add=True)
    last_login_at = models.DateTimeField(auto_now=True)
    provider = models.CharField(max_length=50, blank=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return self.email
    
    def is_site_admin(self):
        return self.role == 'siteAdmin'
    
    def is_venue_admin(self):
        return self.role == 'venueAdmin'
    
    def is_sub_admin(self):
        return self.role == 'subAdmin'
    
    def is_scanner(self):
        return self.role == 'scanner'
    
    def can_manage_venue(self, venue_id=None):
        if self.is_site_admin():
            return True
        if venue_id and self.venue_id == venue_id:
            return self.is_venue_admin() or self.is_sub_admin()
        return False
    
    def can_scan_tickets(self):
        return (self.is_site_admin() or self.is_scanner() or 
                self.is_venue_admin() or self.is_sub_admin())
    
    def get_venue(self):
        """Get the venue object for this user if they have one"""
        if self.venue_id:
            from venues.models import Venue
            return Venue.get_by_id(self.venue_id)
        return None