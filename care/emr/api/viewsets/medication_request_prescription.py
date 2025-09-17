from django_filters import rest_framework as filters
from rest_framework import filters as rest_framework_filters
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRBaseViewSet, EMRModelViewSet, EMRTagMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models.medication_request import MedicationRequestPrescription
from care.emr.resources.medication.request_prescription.spec import (
    MedicationRequestPrescriptionReadSpec,
    MedicationRequestPrescriptionRetrieveDetailedSpec,
    MedicationRequestPrescriptionRetrieveMedicationsSpec,
    MedicationRequestPrescriptionUpdateSpec,
    MedicationRequestPrescriptionWriteSpec,
)
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.filters import SingleFacilityTagFilter
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.shortcuts import get_object_or_404


class MedicationRequestPrescriptionFilter(filters.FilterSet):
    encounter = filters.UUIDFilter(field_name="encounter__external_id")
    status = MultiSelectFilter(field_name="status")
    facility = filters.UUIDFilter(field_name="encounter__facility__external_id")


class MedicationRequestPrescriptionViewSet(
    EncounterBasedAuthorizationBase, EMRModelViewSet, EMRTagMixin
):
    database_model = MedicationRequestPrescription
    pydantic_model = MedicationRequestPrescriptionWriteSpec
    pydantic_update_model = MedicationRequestPrescriptionUpdateSpec
    pydantic_read_model = MedicationRequestPrescriptionReadSpec
    pydantic_retrieve_model = MedicationRequestPrescriptionRetrieveMedicationsSpec
    filterset_class = MedicationRequestPrescriptionFilter
    filter_backends = [
        filters.DjangoFilterBackend,
        rest_framework_filters.OrderingFilter,
        SingleFacilityTagFilter,
    ]
    ordering_fields = ["created_date", "modified_date"]
    resource_type = TagResource.medication_request_prescription

    def get_facility_from_instance(self, instance):
        return instance.encounter.facility  # Overide as needed

    def get_queryset(self):
        self.authorize_read_for_medication()
        return (
            super()
            .get_queryset()
            .filter(patient__external_id=self.kwargs["patient_external_id"])
            .select_related("patient", "encounter", "created_by", "updated_by")
        )


class MedicationRequestSummaryFilters(filters.FilterSet):
    created_date = filters.DateTimeFromToRangeFilter(field_name="created_date")
    status = filters.CharFilter(lookup_expr="iexact")
    patient_external_id = filters.UUIDFilter(field_name="patient__external_id")
    encounter_external_id = filters.UUIDFilter(field_name="encounter__external_id")
    encounter_class = filters.CharFilter(
        field_name="encounter__encounter_class", lookup_expr="iexact"
    )


class MedicationPrescriptionSummaryViewSet(EMRBaseViewSet):
    filter_backends = [filters.DjangoFilterBackend, SingleFacilityTagFilter]
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
        queryset = MedicationRequestPrescription.objects.filter(
            encounter__facility=facility
        ).order_by("-created_date")
        queryset = self.filter_queryset(queryset)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            data = [
                MedicationRequestPrescriptionRetrieveDetailedSpec.serialize(
                    obj
                ).to_json()
                for obj in page
            ]
            return paginator.get_paginated_response(data)
        data = [
            MedicationRequestPrescriptionRetrieveDetailedSpec.serialize(obj).to_json()
            for obj in queryset
        ]
        return Response(data)
