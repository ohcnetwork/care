from dry_rest_permissions.generics import DRYPermissions
from rest_framework import mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.daily_round import DailyRoundSerializer
from care.facility.models.patient_consultation import DailyRound, PatientConsultation


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

    def get_queryset(self):
        queryset = self.queryset.filter(consultation__external_id=self.kwargs["consultation_external_id"])
        return queryset

    def get_serializer(self, *args, **kwargs):
        if "data" in kwargs:
            kwargs["data"]["consultation"] = PatientConsultation.objects.get(
                external_id=self.kwargs["consultation_external_id"]
            ).id
        return super().get_serializer(*args, **kwargs)
