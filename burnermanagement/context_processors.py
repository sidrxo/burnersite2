# burnermanagement/context_processors.py
from django.conf import settings

def firebase_config(request):
    """Make Firebase config available in all templates"""
    return {
        'firebase_config': getattr(settings, 'FIREBASE_WEB_CONFIG', {})
    }