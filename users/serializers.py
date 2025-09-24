from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'display_name', 'role', 'venue_id',
            'created_at', 'last_login_at', 'provider', 'firebase_uid'
        )
        read_only_fields = ('id', 'created_at', 'last_login_at', 'firebase_uid')

class UserProfileSerializer(serializers.ModelSerializer):
    venue_name = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = (
            'id', 'email', 'username', 'display_name', 'role', 'venue_id',
            'created_at', 'last_login_at', 'venue_name', 'permissions'
        )
        read_only_fields = ('id', 'created_at', 'last_login_at', 'email')
    
    def get_venue_name(self, obj):
        venue = obj.get_venue()
        return venue.name if venue else None
    
    def get_permissions(self, obj):
        return {
            'is_site_admin': obj.is_site_admin(),
            'is_venue_admin': obj.is_venue_admin(),
            'is_sub_admin': obj.is_sub_admin(),
            'is_scanner': obj.is_scanner(),
            'can_scan_tickets': obj.can_scan_tickets(),
        }