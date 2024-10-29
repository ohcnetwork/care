from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from care.users.api.serializers.plug_config import PLugConfigSerializer
from care.users.api.viewsets.lsg import PaginataionOverrideClass
from care.users.models import PlugConfig


class PlugConfigViewset(
    ModelViewSet,
    GenericViewSet,
):
    lookup_field = "slug"
    serializer_class = PLugConfigSerializer
    queryset = PlugConfig.objects.all().order_by("slug")
    cache_key = "care_plug_viewset_list"
    authentication_classes = []

    def list(self, request, *args, **kwargs):
        # Cache data and return
        response = cache.get(self.cache_key)
        if not response:
            serializer = self.get_serializer(self.queryset, many=True)
            response = serializer.data
            cache.set(self.cache_key , response)
        return Response({"configs" : [response]})

    def perform_create(self, serializer):
        cache.delete(self.cache_key)
        serializer.save()

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return []
        return [IsAdminUser()]
