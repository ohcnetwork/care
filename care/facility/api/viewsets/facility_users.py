from django.db.models import Prefetch
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import filters as drf_filters
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.models.facility import Facility
from care.users.api.serializers.user import UserAssignedSerializer
from care.users.models import Skill, User


class UserFilter(filters.FilterSet):
    user_type = filters.TypedChoiceFilter(
        choices=[(key, key) for key in User.TYPE_VALUE_MAP.keys()],
        coerce=lambda role: User.TYPE_VALUE_MAP[role],
    )

    class Meta:
        model = User
        fields = []


@extend_schema_view(list=extend_schema(tags=["facility", "users"]))
class FacilityUserViewSet(GenericViewSet, mixins.ListModelMixin):
    serializer_class = UserAssignedSerializer
    filterset_class = UserFilter
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [
        filters.DjangoFilterBackend,
        drf_filters.SearchFilter,
    ]
    search_fields = ["first_name", "last_name", "username"]

    def get_queryset(self):
        try:
            facility = Facility.objects.get(
                external_id=self.kwargs.get("facility_external_id")
            )
            queryset = facility.users.filter(deleted=False).order_by("-last_login")
            queryset = queryset.prefetch_related(
                Prefetch(
                    "skills", queryset=Skill.objects.filter(userskill__deleted=False)
                )
            )
            return queryset
        except Facility.DoesNotExist:
            raise ValidationError({"Facility": "Facility not found"})
