# events/services.py
import os
import uuid
from datetime import datetime
from google.cloud import storage
from firebase_admin import firestore
from django.conf import settings
from burnermanagement.firebase_config import get_firestore_client

class FirestoreEventService:
    """Service class for handling Firestore operations for events"""
    
    def __init__(self):
        self.db = get_firestore_client()
        # Initialize Google Cloud Storage client for image uploads
        try:
            self.storage_client = storage.Client()
            self.bucket_name = "burner-34556.appspot.com"  # Replace with your bucket name
            self.bucket = self.storage_client.bucket(self.bucket_name)
        except Exception as e:
            print(f"Warning: Could not initialize Google Cloud Storage: {e}")
            self.storage_client = None
            self.bucket = None
    
    def upload_image(self, image_file, event_id):
        """Upload image to Google Cloud Storage and return download URL"""
        if not self.storage_client or not image_file:
            return None
        
        try:
            # Generate unique filename
            file_extension = image_file.name.split('.')[-1].lower()
            filename = f"event-images/{event_id}/{uuid.uuid4()}.{file_extension}"
            
            # Upload to bucket
            blob = self.bucket.blob(filename)
            blob.upload_from_file(image_file, content_type=image_file.content_type)
            
            # Make the blob publicly viewable
            blob.make_public()
            
            return blob.public_url
        except Exception as e:
            print(f"Error uploading image: {e}")
            return None
    
    def delete_image(self, image_url):
        """Delete image from Google Cloud Storage"""
        if not self.storage_client or not image_url:
            return
        
        try:
            # Extract blob name from URL
            if self.bucket_name in image_url:
                blob_name = image_url.split(f"{self.bucket_name}/")[-1]
                blob = self.bucket.blob(blob_name)
                blob.delete()
        except Exception as e:
            print(f"Error deleting image: {e}")
    
    def create_event(self, event_data, user, image_file=None):
        """Create a new event in Firestore"""
        if not self.db:
            raise Exception("Firestore client not available")
        
        try:
            event_id = event_data['event_id']
            
            # Check if event already exists
            existing_event = self.db.collection('events').document(event_id).get()
            if existing_event.exists:
                raise Exception("Event with this ID already exists")
            
            # Upload image if provided
            image_url = None
            if image_file:
                image_url = self.upload_image(image_file, event_id)
            
            # Prepare event document
            event_doc = {
                'name': event_data['name'],
                'description': event_data.get('description', ''),
                'venue': event_data['venue_name'],
                'venueId': event_data['venue_id'],
                'date': firestore.SERVER_TIMESTAMP if event_data.get('date') else None,
                'price': float(event_data['price']),
                'maxTickets': int(event_data['max_tickets']),
                'ticketsSold': 0,
                'isFeatured': event_data.get('is_featured', False),
                'createdAt': firestore.SERVER_TIMESTAMP,
                'createdBy': user.email,
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }
            
            # Add image URL if uploaded
            if image_url:
                event_doc['imageUrl'] = image_url
            
            # Convert datetime to Firestore timestamp
            if event_data.get('date'):
                from google.cloud.firestore import SERVER_TIMESTAMP
                # Convert datetime to timestamp
                event_doc['date'] = event_data['date']
            
            # Create the document
            self.db.collection('events').document(event_id).set(event_doc)
            
            return {
                'success': True,
                'event_id': event_id,
                'message': 'Event created successfully'
            }
            
        except Exception as e:
            # Clean up uploaded image if event creation failed
            if 'image_url' in locals() and image_url:
                self.delete_image(image_url)
            raise Exception(f"Failed to create event: {str(e)}")
    
    def update_event(self, event_id, event_data, user, image_file=None):
        """Update an existing event in Firestore"""
        if not self.db:
            raise Exception("Firestore client not available")
        
        try:
            # Get existing event
            event_ref = self.db.collection('events').document(event_id)
            existing_event = event_ref.get()
            
            if not existing_event.exists:
                raise Exception("Event not found")
            
            existing_data = existing_event.to_dict()
            
            # Handle image upload/update
            image_url = existing_data.get('imageUrl')
            if image_file:
                # Delete old image if it exists
                if image_url:
                    self.delete_image(image_url)
                # Upload new image
                image_url = self.upload_image(image_file, event_id)
            
            # Prepare update data
            update_data = {
                'name': event_data['name'],
                'description': event_data.get('description', ''),
                'venue': event_data['venue_name'],
                'venueId': event_data['venue_id'],
                'price': float(event_data['price']),
                'maxTickets': int(event_data['max_tickets']),
                'updatedAt': firestore.SERVER_TIMESTAMP,
            }
            
            # Add image URL if we have one
            if image_url:
                update_data['imageUrl'] = image_url
            
            # Add date if provided
            if event_data.get('date'):
                update_data['date'] = event_data['date']
            
            # Only site admins can update featured status
            if user.is_site_admin():
                update_data['isFeatured'] = event_data.get('is_featured', False)
            
            # Update the document
            event_ref.update(update_data)
            
            return {
                'success': True,
                'event_id': event_id,
                'message': 'Event updated successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to update event: {str(e)}")
    
    def delete_event(self, event_id, user):
        """Delete an event from Firestore"""
        if not self.db:
            raise Exception("Firestore client not available")
        
        try:
            # Get existing event
            event_ref = self.db.collection('events').document(event_id)
            existing_event = event_ref.get()
            
            if not existing_event.exists:
                raise Exception("Event not found")
            
            existing_data = existing_event.to_dict()
            
            # Delete associated tickets (if any)
            tickets_ref = self.db.collection('events').document(event_id).collection('tickets')
            tickets = tickets_ref.stream()
            
            batch = self.db.batch()
            for ticket in tickets:
                batch.delete(ticket.reference)
            batch.commit()
            
            # Delete image if it exists
            if existing_data.get('imageUrl'):
                self.delete_image(existing_data['imageUrl'])
            
            # Delete the event document
            event_ref.delete()
            
            return {
                'success': True,
                'event_id': event_id,
                'message': 'Event deleted successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to delete event: {str(e)}")
    
    def toggle_featured(self, event_id, user):
        """Toggle featured status of an event"""
        if not self.db:
            raise Exception("Firestore client not available")
        
        if not user.is_site_admin():
            raise Exception("Only site administrators can manage featured events")
        
        try:
            event_ref = self.db.collection('events').document(event_id)
            existing_event = event_ref.get()
            
            if not existing_event.exists:
                raise Exception("Event not found")
            
            existing_data = existing_event.to_dict()
            new_featured_status = not existing_data.get('isFeatured', False)
            
            event_ref.update({
                'isFeatured': new_featured_status,
                'updatedAt': firestore.SERVER_TIMESTAMP
            })
            
            action = "featured" if new_featured_status else "unfeatured"
            
            return {
                'success': True,
                'featured': new_featured_status,
                'message': f'Event {action} successfully'
            }
            
        except Exception as e:
            raise Exception(f"Failed to toggle featured status: {str(e)}")

# Create a singleton instance
firestore_event_service = FirestoreEventService()