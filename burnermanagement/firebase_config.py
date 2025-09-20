# burnermanagement/firebase_config.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
from django.conf import settings

_firestore_client = None

def initialize_firebase():
    global _firestore_client
    
    if _firestore_client is not None:
        return _firestore_client
        
    try:
        # Check if Firebase is already initialized
        if not firebase_admin._apps:
            # Try to initialize Firebase
            service_account_path = getattr(settings, 'FIREBASE_SERVICE_ACCOUNT_KEY', None)
            
            if service_account_path and os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                print("Firebase initialized successfully")
            else:
                print(f"Firebase service account key not found at: {service_account_path}")
                print("Admin management will not work without Firebase credentials.")
                _firestore_client = None
                return None
        
        # Get Firestore client
        _firestore_client = firestore.client()
        return _firestore_client
            
    except Exception as e:
        print(f"Firebase initialization failed: {e}")
        _firestore_client = None
        return None

def get_firestore_client():
    return initialize_firebase()