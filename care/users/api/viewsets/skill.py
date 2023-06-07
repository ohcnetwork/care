from rest_framework import filters as drf_filters
from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet

from care.users.api.serializers.skill import SkillSerializer
from care.users.models import Skill


class SkillViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    serializer_class = SkillSerializer
    queryset = Skill.objects.all()
    search_fields = ["name"]
    lookup_field = "external_id"
    filter_backends = (drf_filters.SearchFilter,)
