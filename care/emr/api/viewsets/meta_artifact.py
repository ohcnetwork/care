from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models import Encounter, Patient
from care.emr.models.meta_artifact import MetaArtifact
from care.emr.resources.meta_artifact.spec import (
    MetaArtifactAssociatingTypeChoices,
    MetaArtifactCreateSpec,
    MetaArtifactReadSpec,
    MetaArtifactUpdateSpec,
)
from care.security.authorization import AuthorizationController


class MetaArtifactTypeFilter(filters.CharFilter):
    def filter(self, qs, value):
        if value:
            return qs.filter(object_type__in=value.split(","))
        return qs


class MetaArtifactFilters(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    object_type = MetaArtifactTypeFilter()


def meta_artifact_authorizer(user, associating_type, associating_id, permission):
    allowed = False
    if associating_type == MetaArtifactAssociatingTypeChoices.patient.value:
        patient_obj = get_object_or_404(Patient, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, patient_obj
            )
        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_write_patient_obj", user, patient_obj
            )
    elif associating_type == MetaArtifactAssociatingTypeChoices.encounter.value:
        encounter_obj = get_object_or_404(Encounter, external_id=associating_id)
        if permission == "read":
            allowed = AuthorizationController.call(
                "can_view_clinical_data", user, encounter_obj.patient
            ) or AuthorizationController.call(
                "can_view_encounter_obj", user, encounter_obj
            )

        elif permission == "write":
            allowed = AuthorizationController.call(
                "can_update_encounter_obj", user, encounter_obj
            )

    if not allowed:
        raise PermissionDenied("Cannot view object")


class MetaArtifactViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    database_model = MetaArtifact
    pydantic_model = MetaArtifactCreateSpec
    pydantic_read_model = MetaArtifactReadSpec
    pydantic_update_model = MetaArtifactUpdateSpec
    filterset_class = MetaArtifactFilters
    filter_backends = (filters.DjangoFilterBackend,)

    def authorize_create(self, instance):
        meta_artifact_authorizer(
            self.request.user,
            instance.associating_type,
            instance.associating_id,
            "write",
        )

    def authorize_update(self, request_obj, model_instance):
        meta_artifact_authorizer(
            self.request.user,
            model_instance.associating_type,
            model_instance.associating_external_id,
            "write",
        )

    def get_queryset(self):
        if self.action == "list":
            associating_type = self.request.GET.get("associating_type")
            associating_id = self.request.GET.get("associating_id")
        else:
            obj = get_object_or_404(
                MetaArtifact, external_id=self.kwargs["external_id"]
            )
            associating_type = obj.associating_type
            associating_id = obj.associating_external_id
        if not (associating_type and associating_id):
            raise PermissionDenied(
                "'associating_type' and 'associating_id' are required to retrieve meta artifacts"
            )
        meta_artifact_authorizer(
            self.request.user, associating_type, associating_id, "read"
        )
        return (
            super()
            .get_queryset()
            .filter(
                associating_type=associating_type,
                associating_external_id=associating_id,
            )
            .order_by("-modified_date")
        )
