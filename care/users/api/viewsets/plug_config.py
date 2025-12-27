"""
API views for managing PlugConfig entries.

Provides cached list endpoint and ensures cache invalidation happens
after database writes to avoid stale cache races.
"""

from django.core.cache import cache
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from care.users.api.serializers.plug_config import PlugConfigSerializer
from care.users.models import PlugConfig


class PlugConfigViewset(ModelViewSet, GenericViewSet):
    """
    ViewSet for managing PlugConfig entries.

    List responses are cached for performance and invalidated safely
    after create, update, or delete operations.
    """

    lookup_field = "slug"
    serializer_class = PlugConfigSerializer
    queryset = PlugConfig.objects.all().order_by("slug")
    cache_key = "care_plug_viewset_list"

    def list(self, request, *args, **kwargs):
        """
        Return all PlugConfig records.

        Uses cache-aside strategy and correctly handles cached empty lists.
        """
        response = cache.get(self.cache_key)
        if response is None:  # cache miss; allow cached empty list
            serializer = self.get_serializer(self.get_queryset(), many=True)
            response = serializer.data
            cache.set(self.cache_key, response)
        return Response({"configs": response})

    def perform_create(self, serializer):
        """
        Save a new PlugConfig and invalidate the cached list.

        Cache is cleared after database write to avoid race conditions.
        """
        serializer.save()
        cache.delete(self.cache_key)

    def perform_update(self, serializer):
        """
        Update an existing PlugConfig and invalidate the cached list.

        Cache is cleared after database write to avoid race conditions.
        """
        serializer.save()
        cache.delete(self.cache_key)

    def perform_destroy(self, instance):
        """
        Delete a PlugConfig and invalidate the cached list.

        Cache is cleared after database write to avoid race conditions.
        """
        instance.delete()
        cache.delete(self.cache_key)

    def get_permissions(self):
        """
        Allow unauthenticated access for read operations
        and restrict write operations to admin users.
        """
        if self.action in ["list", "retrieve"]:
            return []
        return [IsAdminUser()]
