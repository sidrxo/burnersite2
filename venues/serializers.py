from rest_framework import serializers
from .models import Venue

class VenueSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    city = serializers.CharField()
    created_at = serializers.DateTimeField(read_only=True)
    admins = serializers.DictField(read_only=True)
    sub_admins = serializers.DictField(read_only=True)
    admin_emails = serializers.ListField(read_only=True, source='get_admin_emails')

class VenueListSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    city = serializers.CharField()