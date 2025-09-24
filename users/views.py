from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .serializers import UserSerializer, UserProfileSerializer

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Site admins can see all users, others only their own profile
        if self.request.user.is_site_admin():
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)

class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user
    
    @action(detail=False, methods=['get'])
    def permissions(self, request):
        """Get current user's permissions"""
        user = request.user
        return Response({
            'role': user.role,
            'venue_id': user.venue_id,
            'permissions': {
                'is_site_admin': user.is_site_admin(),
                'is_venue_admin': user.is_venue_admin(),
                'is_sub_admin': user.is_sub_admin(),
                'is_scanner': user.is_scanner(),
                'can_scan_tickets': user.can_scan_tickets(),
            }
        })