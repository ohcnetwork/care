from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.daily_round import DailyRoundSerializer
from care.facility.api.viewsets.mixins.access import AssetUserAccessMixin
from care.facility.models.daily_round import DailyRound
from care.utils.queryset.consultation import get_consultation_queryset

DailyRoundAttributes = [f.name for f in DailyRound._meta.get_fields()]  # noqa: SLF001


class DailyRoundFilterSet(filters.FilterSet):
    rounds_type = filters.CharFilter(method="filter_rounds_type")
    taken_at = filters.DateTimeFromToRangeFilter()

    def filter_rounds_type(self, queryset, name, value):
        rounds_type = set()
        values = value.upper().split(",")
        for v in values:
            try:
                rounds_type.add(DailyRound.RoundsType[v].value)
            except KeyError:
                pass
        return queryset.filter(rounds_type__in=list(rounds_type))


class DailyRoundsViewSet(
    AssetUserAccessMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    serializer_class = DailyRoundSerializer
    permission_classes = (IsAuthenticated, DRYPermissions)
    queryset = DailyRound.objects.all().select_related("created_by", "last_edited_by")
    lookup_field = "external_id"
    filterset_class = DailyRoundFilterSet

    filter_backends = (filters.DjangoFilterBackend,)

    FIELDS_KEY = "fields"
    MAX_FIELDS = 20
    PAGE_SIZE = 36  # One Round Per Hour

    def get_queryset(self):
        consultation = get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )
        return self.queryset.filter(consultation=consultation).order_by("-taken_at")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["consultation"] = get_object_or_404(
            get_consultation_queryset(self.request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )
        return context

    @extend_schema(tags=["daily_rounds"])
    @action(methods=["POST"], detail=False)
    def analyse(self, request, **kwargs):
        # Request Body Validations

        if self.FIELDS_KEY not in request.data:
            raise ValidationError({"fields": "Field not present"})
        if not isinstance(request.data[self.FIELDS_KEY], list):
            raise ValidationError({"fields": "Must be an List"})
        if len(request.data[self.FIELDS_KEY]) >= self.MAX_FIELDS:
            raise ValidationError({"fields": f"Must be smaller than {self.MAX_FIELDS}"})

        # Request Data Validations

        # Calculate Base Fields ( From . seperated ones )
        base_fields = [str(x).split(".")[0] for x in request.data[self.FIELDS_KEY]]

        errors = {}
        for field in base_fields:
            if field not in DailyRoundAttributes:
                errors[field] = "Not a valid field"

        base_fields.append("external_id")

        if errors:
            raise ValidationError(errors)

        page = request.data.get("page", 1)

        consultation = get_object_or_404(
            get_consultation_queryset(request.user).filter(
                external_id=self.kwargs["consultation_external_id"]
            )
        )
        daily_round_objects = DailyRound.objects.filter(
            consultation=consultation
        ).order_by("-taken_at")
        total_count = daily_round_objects.count()
        daily_round_objects = daily_round_objects[
            ((page - 1) * self.PAGE_SIZE) : ((page * self.PAGE_SIZE) + 1)
        ]
        final_data_rows = daily_round_objects.values("taken_at", *base_fields)
        final_analytics = {}

        for row in final_data_rows:
            if not row["taken_at"]:
                continue
            row_data = {}
            for field in base_fields:
                row_data[field] = row[field]
            row_data["id"] = row["external_id"]
            del row_data["external_id"]
            final_analytics[str(row["taken_at"])] = row_data
        final_data = {
            "results": final_analytics,
            "count": total_count,
            "page_size": self.PAGE_SIZE,
        }
        return Response(final_data)
