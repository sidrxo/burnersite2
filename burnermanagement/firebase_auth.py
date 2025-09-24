import firebase_admin
from firebase_admin import auth
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import BaseBackend
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from .firebase_config import get_firebase_app
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class FirebaseAuthenticationBackend(BaseBackend):
    """Django authentication backend for Firebase"""
    
    def authenticate(self, request, firebase_user=None, **kwargs):
        if firebase_user is None:
            return None
            
        try:
            # Get or create user based on Firebase user
            user, created = User.objects.get_or_create(
                firebase_uid=firebase_user.uid,
                defaults={
                    'email': firebase_user.email,
                    'username': firebase_user.email,
                    'display_name': firebase_user.display_name or '',
                    'provider': 'firebase'
                }
            )
            
            if created:
                logger.info(f"Created new user from Firebase: {user.email}")
            
            return user
            
        except Exception as e:
            logger.error(f"Error in Firebase authentication: {e}")
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class FirebaseAuthentication(BaseAuthentication):
    """DRF Authentication class for Firebase tokens"""
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
            
        token = auth_header.split(' ')[1]
        
        try:
            # Verify the Firebase token
            app = get_firebase_app()
            if not app:
                return None
                
            decoded_token = auth.verify_id_token(token, app=app)
            firebase_uid = decoded_token['uid']
            
            # Get or create user
            try:
                user = User.objects.get(firebase_uid=firebase_uid)
            except User.DoesNotExist:
                # Create user if doesn't exist
                user = User.objects.create(
                    firebase_uid=firebase_uid,
                    email=decoded_token.get('email', ''),
                    username=decoded_token.get('email', firebase_uid),
                    display_name=decoded_token.get('name', ''),
                    provider='firebase'
                )
                
            return (user, token)
            
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            raise AuthenticationFailed('Invalid Firebase token')