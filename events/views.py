from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from .models import Event
from .serializers import EventSerializer, EventListSerializer

class EventViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def list(self, request):
        """Get all active events"""
        events = Event.get_all_active()
        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get specific event"""
        event = Event.get_by_id(pk)
        if not event:
            return Response(
                {'error': 'Event not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = EventSerializer(event)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Get featured events"""
        limit = int(request.query_params.get('limit', 6))
        events = Event.get_featured(limit=limit)
        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def by_venue(self, request):
        """Get events by venue"""
        venue_id = request.query_params.get('venue_id')
        if not venue_id:
            return Response(
                {'error': 'venue_id parameter required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        events = Event.get_by_venue(venue_id)
        serializer = EventListSerializer(events, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def toggle_featured(self, request, pk=None):
        """Toggle featured status (admin only)"""
        if not request.user.is_site_admin():
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        success = Event.toggle_featured(pk)
        if success:
            return Response({'message': 'Featured status toggled'})
        return Response(
            {'error': 'Failed to toggle featured status'}, 
            status=status.HTTP_400_BAD_REQUEST
        )