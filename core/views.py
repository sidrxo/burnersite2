from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from venues.models import Venue
from events.models import Event

class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({
            'status': 'healthy',
            'message': 'Burner API is running'
        }, status=status.HTTP_200_OK)

class StatusView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        # Get basic stats
        venues_count = Venue.count_active()
        events = Event.get_all_active()
        events_count = len(events)
        
        return Response({
            'api_version': '1.0',
            'status': 'operational',
            'stats': {
                'venues': venues_count,
                'events': events_count,
                'featured_events': len([e for e in events if e.is_featured])
            }
        })