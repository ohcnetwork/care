from django.db.models import Count
from django_filters import rest_framework as filters
from rest_framework import filters as rest_framework_filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRModelViewSet,
    EMRQuestionnaireResponseMixin,
)
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequest
from care.emr.registries.system_questionnaire.system_questionnaire import (
    InternalQuestionnaireRegistry,
)
from care.emr.resources.encounter.spec import EncounterListSpec
from care.emr.resources.medication.request.spec import (
    MedicationRequestReadSpec,
    MedicationRequestSpec,
    MedicationRequestStatus,
    MedicationRequestUpdateSpec,
)
from care.emr.resources.questionnaire.spec import SubjectType
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.filters.null_filter import NullFilter
from care.utils.shortcuts import get_object_or_404


class MedicationRequestFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    status = MultiSelectFilter(field_name="status")
    name = filters.CharFilter(field_name="medication__display", lookup_expr="icontains")
    encounter_class = filters.CharFilter(
        field_name="encounter__class", lookup_expr="iexact"
    )
    priority = filters.CharFilter(lookup_expr="iexact")
    dispense_status = MultiSelectFilter(field_name="dispense_status")
    exclude_dispense_status = MultiSelectFilter(
        field_name="dispense_status", exclude=True
    )
    dispense_status_isnull = NullFilter(field_name="dispense_status")
    facility = filters.UUIDFilter(field_name="encounter__facility__external_id")


class MedicationRequestViewSet(
    EncounterBasedAuthorizationBase, EMRQuestionnaireResponseMixin, EMRModelViewSet
):
    database_model = MedicationRequest
    pydantic_model = MedicationRequestSpec
    pydantic_read_model = MedicationRequestReadSpec
    pydantic_update_model = MedicationRequestUpdateSpec
    questionnaire_type = "medication_request"
    questionnaire_title = "Medication Request"
    questionnaire_description = "Medication Request"
    questionnaire_subject_type = SubjectType.patient.value
    filterset_class = MedicationRequestFilter
    filter_backends = [
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
    ]
    ordering_fields = ["created_date", "modified_date"]

    def get_queryset(self):
        self.authorize_read_for_medication()
        return (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "created_by", "updated_by")
        )

    def authorize_create(self, instance):
        super().authorize_create(instance)
        if instance.requester:
            encounter = get_object_or_404(Encounter, external_id=instance.encounter)
            requester = get_object_or_404(User, external_id=instance.requester)
            if not AuthorizationController.call(
                "can_update_encounter_obj", requester, encounter
            ):
                raise PermissionDenied(
                    "Requester does not have permission to update encounter"
                )


InternalQuestionnaireRegistry.register(MedicationRequestViewSet)


class MedicationRequestSummaryFilters(filters.FilterSet):
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")
    status = filters.CharFilter(lookup_expr="iexact")
    intent = filters.CharFilter(lookup_expr="iexact")
    priority = filters.CharFilter(lookup_expr="iexact")
    category = filters.CharFilter(lookup_expr="iexact")
    patient_external_id = filters.UUIDFilter(field_name="patient__external_id")
    encounter_external_id = filters.UUIDFilter(field_name="encounter__external_id")
    dispense_status = MultiSelectFilter(field_name="dispense_status")
    exclude_dispense_status = MultiSelectFilter(
        field_name="dispense_status", exclude=True
    )
    dispense_status_isnull = NullFilter(field_name="dispense_status")
    encounter_class = filters.CharFilter(
        field_name="encounter__encounter_class", lookup_expr="iexact"
    )


class MedicationRequestSummaryViewSet(EMRBaseViewSet):
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = MedicationRequestSummaryFilters

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def authorize_for_pharmacist(self, facility):
        if not AuthorizationController.call(
            "can_view_as_pharmacist", self.request.user, facility
        ):
            raise PermissionDenied("You do not have permission to view this facility")

    @action(methods=["GET"], detail=False)
    def summary(self, request, *args, **kwargs):
        facility = self.get_facility_obj()
        self.authorize_for_pharmacist(facility)
        queryset = (
            MedicationRequest.objects.filter(
                encounter__facility=facility,
                status=MedicationRequestStatus.active.value,
            )
            .values("encounter_id", "priority")
            .annotate(dcount=Count("priority"))
        ).order_by("encounter_id")
        queryset = self.filter_queryset(queryset)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            encounters = Encounter.objects.filter(
                id__in=[x["encounter_id"] for x in page]
            )
            encounters = {
                x.id: EncounterListSpec.serialize(x).to_json() for x in encounters
            }
            data = [
                {
                    "encounter": encounters.get(x["encounter_id"], None),
                    "priority": x["priority"],
                    "count": x["dcount"],
                }
                for x in page
            ]
            return paginator.get_paginated_response(data)
        return Response({})
