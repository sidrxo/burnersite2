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
            
            logger.info(f"Firebase token decoded - UID: {uid}, Email: {email}")
            
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
            
            logger.info(f"Checking admin doc for UID: {uid}")
            logger.info(f"Admin doc exists: {admin_doc.exists}")
            
            user_data = {
                'email': email,
                'username': email,
                'role': 'user',  # default role
                'venue_id': '',
                'display_name': email.split('@')[0],
                'firebase_uid': uid,  # IMPORTANT: Set the Firebase UID
            }
            
            if admin_doc.exists:
                # This is an admin user
                admin_data = admin_doc.to_dict()
                logger.info(f"Admin data found: {admin_data}")
                
                extracted_role = admin_data.get('role', 'user')
                extracted_venue_id = admin_data.get('venueId', '')
                extracted_display_name = admin_data.get('displayName', email.split('@')[0])
                
                logger.info(f"Extracted role: {extracted_role}")
                logger.info(f"Extracted venue_id: {extracted_venue_id}")
                logger.info(f"Extracted display_name: {extracted_display_name}")
                
                user_data.update({
                    'role': extracted_role,
                    'venue_id': extracted_venue_id,
                    'display_name': extracted_display_name,
                })
            else:
                logger.info(f"No admin doc found for UID: {uid}, checking regular users collection")
                # Check if regular user exists in Firestore /users/ collection
                user_doc = db.collection('users').document(uid).get()
                logger.info(f"Regular user doc exists: {user_doc.exists}")
                
                if user_doc.exists:
                    user_firestore_data = user_doc.to_dict()
                    logger.info(f"Regular user data found: {user_firestore_data}")
                    user_data.update({
                        'display_name': user_firestore_data.get('displayName', email.split('@')[0]),
                        'role': user_firestore_data.get('role', 'user'),
                    })
            
            logger.info(f"Final user_data before Django user creation: {user_data}")
            
            # Create or update Django user
            User = get_user_model()
            
            # Try to get user by firebase_uid first, then by email
            user = None
            try:
                user = User.objects.get(firebase_uid=uid)
                logger.info(f"Found existing user by firebase_uid: {user.email}")
                created = False
            except User.DoesNotExist:
                try:
                    user = User.objects.get(email=email)
                    logger.info(f"Found existing user by email: {user.email}")
                    created = False
                except User.DoesNotExist:
                    logger.info(f"Creating new user with email: {email}")
                    user = User.objects.create(**user_data)
                    created = True
            
            # Update existing user data if not created
            if not created:
                logger.info(f"Updating existing user. Current role: {user.role}")
                for key, value in user_data.items():
                    old_value = getattr(user, key, None)
                    setattr(user, key, value)
                    if old_value != value:
                        logger.info(f"Updated {key}: {old_value} -> {value}")
                user.save()
                logger.info(f"User saved. New role: {user.role}")
            
            logger.info(f"Firebase authentication successful for {email} with role: {user.role}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to get/create Django user: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
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
                firebase_uid=user_record.uid,  # IMPORTANT: Set Firebase UID
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
            
            # Update Django user too
            try:
                User = get_user_model()
                # Try to find by firebase_uid first, then by email
                django_user = None
                try:
                    django_user = User.objects.get(firebase_uid=uid)
                except User.DoesNotExist:
                    firebase_user = auth.get_user(uid)
                    django_user = User.objects.get(email=firebase_user.email)
                
                django_user.role = new_role
                if new_venue_id is not None:
                    django_user.venue_id = new_venue_id
                django_user.firebase_uid = uid  # Ensure this is set
                django_user.save()
            except Exception as django_error:
                logger.warning(f"Could not update Django user: {django_error}")
            
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
            # Get user email before deletion for Django cleanup
            try:
                firebase_user = auth.get_user(uid)
                email = firebase_user.email
                
                # Delete Django user if exists
                User = get_user_model()
                try:
                    # Try to find by firebase_uid first, then by email
                    try:
                        django_user = User.objects.get(firebase_uid=uid)
                    except User.DoesNotExist:
                        django_user = User.objects.get(email=email)
                    django_user.delete()
                except User.DoesNotExist:
                    pass
            except:
                pass
            
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
    
    def _generate_secure_password(self, length=12):
        """Generate a secure random password"""
        characters = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(secrets.choice(characters) for _ in range(length))
        return password