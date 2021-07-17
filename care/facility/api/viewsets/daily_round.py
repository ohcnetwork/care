from datetime import datetime, timedelta
from uuid import uuid4

from django.utils import timezone
from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.daily_round import DailyRoundSerializer
from care.facility.models.daily_round import DailyRound
from care.facility.models.patient_consultation import PatientConsultation
from care.utils.queryset.consultation import get_consultation_queryset

DailyRoundAttributes = [f.name for f in DailyRound._meta.get_fields()]


class DailyRoundsViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.UpdateModelMixin, GenericViewSet
):
    serializer_class = DailyRoundSerializer
    permission_classes = (
        IsAuthenticated,
        DRYPermissions,
    )
    queryset = DailyRound.objects.all().order_by("-id")
    lookup_field = "external_id"

    DEFAULT_LOOKUP_DAYS = 2
    FIELDS_KEY = "fields"
    MAX_FIELDS = 10

    def get_queryset(self):
        queryset = self.queryset.filter(consultation__external_id=self.kwargs["consultation_external_id"])
        return queryset

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            kwargs["data"]["consultation"] = PatientConsultation.objects.get(
                external_id=self.kwargs["consultation_external_id"]
            ).id
        return super().get_serializer(*args, **kwargs)

    @action(methods=["POST"], detail=False)
    def clone_last(self, request, **kwargs):
        consultation = get_object_or_404(
            get_consultation_queryset(request.user).filter(external_id=self.kwargs["consultation_external_id"])
        )
        last_objects = DailyRound.objects.filter(consultation=consultation).order_by("-created_date")
        if not last_objects.exists():
            raise ValidationError({"daily_round": "No Daily Round objects available to clone"})
        cloned_daily_round_obj = last_objects[0]
        cloned_daily_round_obj.pk = None
        cloned_daily_round_obj.created_date = timezone.now()
        cloned_daily_round_obj.modified_date = timezone.now()
        cloned_daily_round_obj.external_id = uuid4()
        cloned_daily_round_obj.save()
        return Response({"id": cloned_daily_round_obj.external_id})

    @action(methods=["POST"], detail=False)
    def analyse(self, request, **kwargs):

        # Request Body Validations

        if self.FIELDS_KEY not in request.data:
            raise ValidationError({"fields": "Field not present"})
        if not isinstance(request.data[self.FIELDS_KEY], list):
            raise ValidationError({"fields": "Must be an List"})
        if len(request.data[self.FIELDS_KEY]) >= self.MAX_FIELDS:
            raise ValidationError({"fields": "Must be smaller than {}".format(self.MAX_FIELDS)})

        # Request Data Validations

        # Calculate Base Fields ( From . seperated ones )
        base_fields = [str(x).split(".")[0] for x in request.data[self.FIELDS_KEY]]

        errors = {}
        for field in base_fields:
            if field not in DailyRoundAttributes:
                errors[field] = "Not a valid field"

        if errors:
            raise ValidationError(errors)

        page = request.data.get("page", 1)
        to_time = datetime.now() - timedelta(days=((page - 1) * self.DEFAULT_LOOKUP_DAYS))
        from_time = to_time - timedelta(days=self.DEFAULT_LOOKUP_DAYS)

        consultation = get_object_or_404(
            get_consultation_queryset(request.user).filter(external_id=self.kwargs["consultation_external_id"])
        )
        daily_round_objects = DailyRound.objects.filter(
            consultation=consultation, taken_at__gt=from_time, taken_at__lt=to_time
        ).order_by("-taken_at")

        final_data_rows = daily_round_objects.values("taken_at", *base_fields)
        final_analytics = {}
        for row in final_data_rows:
            print(row["taken_at"])
            if not row["taken_at"]:
                continue
            row_data = {}
            for field in base_fields:
                row_data[field] = row[field]
            final_analytics[str(row["taken_at"])] = row_data

        return Response(final_analytics)
