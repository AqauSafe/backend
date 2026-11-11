"""Sync request validation serializers."""

from rest_framework import serializers


class SyncImportSerializer(serializers.Serializer):
    farms = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    ponds = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    feedings = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    readings = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    listings = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    messages = serializers.ListField(child=serializers.DictField(), required=False, default=list)
