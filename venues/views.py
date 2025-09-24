from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from .models import Venue
from .serializers import VenueSerializer, VenueListSerializer

class VenueViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def list(self, request):
        """Get all active venues"""
        venues = Venue.get_all_active()
        serializer = VenueListSerializer(venues, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Get specific venue"""
        venue = Venue.get_by_id(pk)
        if not venue:
            return Response(
                {'error': 'Venue not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        serializer = VenueSerializer(venue)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def count(self, request):
        """Get venue count"""
        count = Venue.count_active()
        return Response({'count': count})