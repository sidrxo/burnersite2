# burnermanagement/firebase_auth.py
import firebase_admin
from firebase_admin import auth, firestore
from django.conf import settings
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from datetime import datetime
import logging
import secrets
import string

logger = logging.getLogger(__name__)

class FirebaseAuthenticationBackend(BaseBackend):
    """
    Django authentication backend that validates Firebase ID tokens
    and creates/updates Django users based on Firestore /admins/ collection
    """
    
    def authenticate(self, request, firebase_token=None, **kwargs):
        if not firebase_token:
            return None
        
        try:
            # Verify the Firebase ID token
            decoded_token = auth.verify_id_token(firebase_token)
            uid = decoded_token['uid']
            email = decoded_token.get('email')
            
            if not email:
                return None
            
            # Get admin user data from Firestore /admins/ collection
            db = firestore.client()
            admin_doc = db.collection('admins').document(uid).get()
            
            if not admin_doc.exists:
                logger.warning(f"No admin document found for UID: {uid}")
                return None
            
            admin_data = admin_doc.to_dict()
            role = admin_data.get('role', 'user')
            
            # Only allow admin roles to access Django interface
            if role not in ['siteAdmin', 'venueAdmin', 'subAdmin']:
                logger.warning(f"User {email} has invalid role: {role}")
                return None
            
            # Create or update Django user
            User = get_user_model()
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': email,
                    'first_name': admin_data.get('displayName', '').split(' ')[0],
                    'last_name': ' '.join(admin_data.get('displayName', '').split(' ')[1:]),
                    'role': role,
                    'venue_id': admin_data.get('venueId', ''),
                    'display_name': admin_data.get('displayName', ''),
                }
            )
            
            # Update role and venue if changed
            if not created:
                user.role = role
                user.venue_id = admin_data.get('venueId', '')
                user.display_name = admin_data.get('displayName', '')
                user.save()
            
            return user
            
        except Exception as e:
            logger.error(f"Firebase authentication failed: {e}")
            return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class FirebaseAdminManager:
    """Helper class for managing admin users in Firebase/Firestore /admins/ collection"""
    
    def __init__(self):
        from burnermanagement.firebase_config import get_firestore_client
        self.db = get_firestore_client()
        self.admin_collection = 'admins'  # Use /admins/ collection
    
    def create_admin_user(self, email, role, venue_id=None, display_name=None):
        """Create a new admin user in Firebase Auth and Firestore /admins/ collection"""
        if not self.db:
            raise Exception("Firebase not initialized. Check your service account key.")
            
        if role not in ['siteAdmin', 'venueAdmin', 'subAdmin']:
            raise ValueError("Invalid role. Must be siteAdmin, venueAdmin, or subAdmin")
        
        if role in ['venueAdmin', 'subAdmin'] and not venue_id:
            raise ValueError("venueAdmin and subAdmin must have a venue_id")
        
        try:
            # Check if admin already exists
            existing_admin = self.get_admin_by_email(email)
            if existing_admin:
                raise ValueError(f"Admin with email {email} already exists")
            
            # Create user in Firebase Auth
            user_record = auth.create_user(
                email=email,
                display_name=display_name or email.split('@')[0],
                email_verified=False
            )
            
            # Create admin document in Firestore /admins/ collection
            admin_data = {
                'email': email,
                'displayName': display_name or email.split('@')[0],
                'role': role,
                'venueId': venue_id or '',
                'createdAt': firestore.SERVER_TIMESTAMP,
                'createdBy': 'django-admin',
                'isActive': True,
                'emailVerified': False,
                'passwordSet': False,
                'provider': 'email'
            }
            
            self.db.collection(self.admin_collection).document(user_record.uid).set(admin_data)
            
            # Generate password reset link for account setup
            reset_link = auth.generate_password_reset_link(email)
            logger.info(f"Password setup link for {email}: {reset_link}")
            
            logger.info(f"Created admin user: {email} with role: {role}")
            return user_record.uid
            
        except Exception as e:
            # Cleanup if creation fails
            try:
                if 'user_record' in locals():
                    auth.delete_user(user_record.uid)
            except:
                pass
            logger.error(f"Failed to create admin user: {e}")
            raise
    
    def update_admin_role(self, uid, new_role, new_venue_id=None):
        """Update admin user's role and venue by UID"""
        if not self.db:
            raise Exception("Firebase not initialized")
            
        try:
            update_data = {
                'role': new_role,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }
            
            if new_venue_id is not None:
                update_data['venueId'] = new_venue_id
            
            self.db.collection(self.admin_collection).document(uid).update(update_data)
            logger.info(f"Updated admin {uid} role to {new_role}")
            
        except Exception as e:
            logger.error(f"Failed to update admin role: {e}")
            raise
    
    def get_admin_by_email(self, email):
        """Get admin by email from /admins/ collection"""
        if not self.db:
            return None
            
        try:
            user_record = auth.get_user_by_email(email)
            admin_doc = self.db.collection(self.admin_collection).document(user_record.uid).get()
            
            if admin_doc.exists:
                admin_data = admin_doc.to_dict()
                admin_data['uid'] = user_record.uid
                admin_data['firebase_user'] = user_record
                return admin_data
            return None
            
        except Exception as e:
            logger.error(f"Failed to get admin by email: {e}")
            return None
    
    def list_admin_users(self):
        """List all admin users from /admins/ collection"""
        if not self.db:
            logger.error("Firebase not initialized")
            return []
            
        try:
            admin_users = []
            docs = self.db.collection(self.admin_collection).stream()
            
            for doc in docs:
                admin_data = doc.to_dict()
                admin_data['uid'] = doc.id
                
                # Get additional Firebase Auth data
                try:
                    firebase_user = auth.get_user(doc.id)
                    admin_data['disabled'] = firebase_user.disabled
                    admin_data['email_verified'] = firebase_user.email_verified
                except:
                    admin_data['disabled'] = False
                    admin_data['email_verified'] = False
                
                admin_users.append(admin_data)
            
            return admin_users
            
        except Exception as e:
            logger.error(f"Failed to list admin users: {e}")
            return []
    
    def activate_admin(self, uid):
        """Activate an admin account"""
        if not self.db:
            raise Exception("Firebase not initialized")
            
        try:
            auth.update_user(uid, disabled=False)
            
            self.db.collection(self.admin_collection).document(uid).update({
                'isActive': True,
                'reactivatedAt': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Activated admin: {uid}")
            
        except Exception as e:
            logger.error(f"Failed to activate admin: {e}")
            raise
    
    def deactivate_admin(self, uid):
        """Deactivate an admin account"""
        if not self.db:
            raise Exception("Firebase not initialized")
            
        try:
            auth.update_user(uid, disabled=True)
            
            self.db.collection(self.admin_collection).document(uid).update({
                'isActive': False,
                'deactivatedAt': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"Deactivated admin: {uid}")
            
        except Exception as e:
            logger.error(f"Failed to deactivate admin: {e}")
            raise
    
    def delete_admin(self, uid):
        """Permanently delete an admin account"""
        if not self.db:
            raise Exception("Firebase not initialized")
            
        try:
            auth.delete_user(uid)
            self.db.collection(self.admin_collection).document(uid).delete()
            
            logger.info(f"Deleted admin: {uid}")
            
        except Exception as e:
            logger.error(f"Failed to delete admin: {e}")
            raise
    
    def send_password_reset(self, email):
        """Send password reset email"""
        try:
            reset_link = auth.generate_password_reset_link(email)
            logger.info(f"Generated password reset link for: {email}")
            return reset_link
            
        except Exception as e:
            logger.error(f"Failed to generate password reset: {e}")
            raise