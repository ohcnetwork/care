from django.core.cache import cache
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from care.users.api.serializers.plug_config import PlugConfigSerializer
from care.users.models import PlugConfig


class PlugConfigViewset(ModelViewSet, GenericViewSet):
    lookup_field = "slug"
    serializer_class = PlugConfigSerializer
    queryset = PlugConfig.objects.all().order_by("slug")
    cache_key = "care_plug_viewset_list"

    def list(self, request, *args, **kwargs):
        response = cache.get(self.cache_key)
        if response is None:
            serializer = self.get_serializer(self.get_queryset(), many=True)
            response = serializer.data
            cache.set(self.cache_key, response)
        return Response({"configs": response})

    def perform_create(self, serializer):
        serializer.save()
        cache.delete(self.cache_key)

    def perform_update(self, serializer):
        serializer.save()
        cache.delete(self.cache_key)

    def perform_destroy(self, instance):
        instance.delete()
        cache.delete(self.cache_key)

    def get_authenticators(self):
        if getattr(self, "request", None) and self.request.method == "GET":
            return []
        return super().get_authenticators()

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return []
        return [IsAdminUser()]
