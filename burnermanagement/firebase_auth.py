# burnermanagement/firebase_auth.py (Firebase-only version)
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
    Firebase-only authentication backend
    """
    
    def authenticate(self, request, firebase_token=None, **kwargs):
        """Only authenticate with Firebase tokens"""
        if firebase_token:
            return self._authenticate_with_token(firebase_token)
        return None
    
    def _authenticate_with_token(self, firebase_token):
        """Authenticate using Firebase ID token"""
        try:
            # Verify the Firebase ID token
            decoded_token = auth.verify_id_token(firebase_token)
            uid = decoded_token['uid']
            email = decoded_token.get('email')
            
            if not email:
                logger.error("No email in Firebase token")
                return None
            
            return self._get_or_create_django_user(uid, email, decoded_token)
            
        except Exception as e:
            logger.error(f"Firebase token authentication failed: {e}")
            return None
    
    def _get_or_create_django_user(self, uid, email, firebase_data=None):
        """Get or create Django user from Firebase user data"""
        try:
            # Check if user exists in Firestore /admins/ collection
            db = firestore.client()
            admin_doc = db.collection('admins').document(uid).get()
            
            user_data = {
                'email': email,
                'username': email,
                'role': 'user',  # default role
                'venue_id': '',
                'display_name': email.split('@')[0],
            }
            
            if admin_doc.exists:
                # This is an admin user
                admin_data = admin_doc.to_dict()
                user_data.update({
                    'role': admin_data.get('role', 'user'),
                    'venue_id': admin_data.get('venueId', ''),
                    'display_name': admin_data.get('displayName', email.split('@')[0]),
                })
            else:
                # Check if regular user exists in Firestore /users/ collection
                user_doc = db.collection('users').document(uid).get()
                if user_doc.exists:
                    user_firestore_data = user_doc.to_dict()
                    user_data.update({
                        'display_name': user_firestore_data.get('displayName', email.split('@')[0]),
                        'role': user_firestore_data.get('role', 'user'),
                    })
            
            # Create or update Django user
            User = get_user_model()
            user, created = User.objects.get_or_create(
                email=email,
                defaults=user_data
            )
            
            # Update existing user data
            if not created:
                for key, value in user_data.items():
                    setattr(user, key, value)
                user.save()
            
            logger.info(f"Firebase authentication successful for {email}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to get/create Django user: {e}")
            return None
    
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class FirebaseAdminManager:
    """Firebase admin manager - no Django password storage"""
    
    def __init__(self):
        from burnermanagement.firebase_config import get_firestore_client
        self.db = get_firestore_client()
        self.admin_collection = 'admins'
    
    def create_admin_user(self, email, role, venue_id=None, display_name=None, password=None):
        """Create admin user in Firebase Auth and Firestore only"""
        if not self.db:
            raise Exception("Firebase not initialized. Check your service account key.")
            
        if role not in ['siteAdmin', 'venueAdmin', 'subAdmin']:
            raise ValueError("Invalid role. Must be siteAdmin, venueAdmin, or subAdmin")
        
        if role in ['venueAdmin', 'subAdmin'] and not venue_id:
            raise ValueError("venueAdmin and subAdmin must have a venue_id")
        
        try:
            # Check if admin already exists in Firebase
            try:
                existing_user = auth.get_user_by_email(email)
                raise ValueError(f"User with email {email} already exists in Firebase")
            except auth.UserNotFoundError:
                pass  # Good, user doesn't exist
            
            # Generate a secure password if not provided
            if not password:
                password = self._generate_secure_password()
            
            # Create user in Firebase Auth
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=display_name or email.split('@')[0],
                email_verified=True  # Set to True for admin users
            )
            
            # Create admin document in Firestore
            admin_data = {
                'email': email,
                'displayName': display_name or email.split('@')[0],
                'role': role,
                'venueId': venue_id or '',
                'createdAt': firestore.SERVER_TIMESTAMP,
                'createdBy': 'admin-management',
                'isActive': True,
                'emailVerified': True,
                'passwordSet': True,
                'provider': 'email'
            }
            
            self.db.collection(self.admin_collection).document(user_record.uid).set(admin_data)
            
            # Create minimal Django user record (no password stored)
            User = get_user_model()
            django_user = User.objects.create(
                email=email,
                username=email,
                role=role,
                venue_id=venue_id or '',
                display_name=display_name or email.split('@')[0],
                # Don't set password - Firebase handles authentication
            )
            
            logger.info(f"Created admin user: {email} with role: {role}")
            
            return {
                'uid': user_record.uid,
                'email': email,
                'password': password,  # Return for initial setup
                'firebase_user': user_record,
                'django_user': django_user
            }
            
        except Exception as e:
            # Cleanup if creation fails
            try:
                if 'user_record' in locals():
                    auth.delete_user(user_record.uid)
            except:
                pass
            try:
                if 'django_user' in locals():
                    django_user.delete()
            except:
                pass
            logger.error(f"Failed to create admin user: {e}")
            raise
    
    # ... rest of the methods remain the same ...