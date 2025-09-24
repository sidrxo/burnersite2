from rest_framework import serializers
from .models import Event

class EventSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField()
    venue = serializers.CharField()
    venue_id = serializers.CharField()
    date = serializers.DateTimeField()
    price = serializers.FloatField()
    max_tickets = serializers.IntegerField()
    tickets_sold = serializers.IntegerField(read_only=True)
    tickets_remaining = serializers.IntegerField(read_only=True)
    image_url = serializers.URLField()
    is_featured = serializers.BooleanField()
    created_at = serializers.DateTimeField(read_only=True)
    created_by = serializers.CharField(read_only=True)
    is_sold_out = serializers.BooleanField(read_only=True)
    is_upcoming = serializers.BooleanField(read_only=True)
    event_status = serializers.CharField(read_only=True)

class EventListSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField()
    venue = serializers.CharField()
    date = serializers.DateTimeField()
    price = serializers.FloatField()
    tickets_remaining = serializers.IntegerField(read_only=True)
    image_url = serializers.URLField()
    is_featured = serializers.BooleanField()
    event_status = serializers.CharField(read_only=True)