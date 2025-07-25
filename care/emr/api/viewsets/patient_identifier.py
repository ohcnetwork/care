from django.shortcuts import get_object_or_404
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
)
from care.emr.models.patient import (
    PatientIdentifierConfig,
    PatientIdentifierConfigCache,
)
from care.emr.resources.patient_identifier.spec import (
    BasePatientIdentifierSpec,
    PatientIdentifierCreateSpec,
    PatientIdentifierListSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController


class PatientIdentifierConfigFilters(filters.FilterSet):
    facility = filters.UUIDFilter(field_name="facility__external_id")
    status = (filters.CharFilter(lookup_expr="iexact")
    display = filters.CharFilter(field_name="config__display", lookup_expr="icontains")


class PatientIdentifierConfigViewSet(
    EMRCreateMixin, EMRRetrieveMixin, EMRUpdateMixin, EMRListMixin, EMRBaseViewSet
):
    database_model = PatientIdentifierConfig
    pydantic_model = PatientIdentifierCreateSpec
    pydantic_update_model = BasePatientIdentifierSpec
    pydantic_read_model = PatientIdentifierListSpec
    filterset_class = PatientIdentifierConfigFilters
    filter_backends = [filters.DjangoFilterBackend]

    def authorize_create(self, instance):
        if instance.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_write_facility_patient_identifier_config",
                self.request.user,
                facility,
            ):
                raise PermissionDenied(
                    "You do not have permission to write patient identifier configs"
                )
        if not instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied(
                "You are not authorized to create a patient identifier config"
            )

    def authorize_update(self, request_obj, model_instance):
        if model_instance.facility:
            facility = get_object_or_404(Facility, external_id=model_instance.facility)
            if not AuthorizationController.call(
                "can_write_facility_patient_identifier_config",
                self.request.user,
                facility,
            ):
                raise PermissionDenied(
                    "You do not have permission to write patient identifier configs"
                )
        if not model_instance.facility and not self.request.user.is_superuser:
            raise PermissionDenied(
                "You are not authorized to update a patient identifier config"
            )

    def clean_cache(self, instance):
        if instance.facility:
            PatientIdentifierConfigCache.clear_facility_cache(instance.facility_id)
        else:
            PatientIdentifierConfigCache.clear_instance_cache()

    def perform_create(self, instance):
        self.clean_cache(instance)
        return super().perform_create(instance)

    def perform_update(self, instance):
        self.clean_cache(instance)
        return super().perform_update(instance)

    def validate_data(self, instance, model_obj=None):
        # Validate that the system is not present at the instance or the facility level
        # System can be duplicated within multiple facilties
        queryset = super().get_queryset().filter(config__system=instance.config.system)
        if model_obj:
            queryset = queryset.exclude(id=model_obj.id)
        if queryset.filter(facility__isnull=True).exists():
            raise ValidationError(
                "A patient identifier config with this system already exists"
            )
        if model_obj and model_obj.facility:
            queryset = queryset.filter(facility=model_obj.facility)
        elif getattr(instance, "facility", None):
            queryset = queryset.filter(facility__external_id=instance.facility)
        if queryset.exists():
            raise ValidationError(
                "A patient identifier config with this system already exists in this facility"
            )

    def authorize_retrieve(self, model_instance):
        if model_instance.facility:
            facility = get_object_or_404(Facility, external_id=model_instance.facility)
            if not AuthorizationController.call(
                "can_list_facility_patient_identifier_config",
                self.request.user,
                facility,
            ):
                raise PermissionDenied(
                    "You do not have permission to read patient identifier configs"
                )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "list":
            if "facility" in self.request.GET:
                facility = get_object_or_404(
                    Facility, external_id=self.request.GET["facility"]
                )
                if not AuthorizationController.call(
                    "can_list_facility_patient_identifier_config",
                    self.request.user,
                    facility,
                ):
                    raise PermissionDenied(
                        "You do not have permission to read patient identifier configs"
                    )
                queryset = queryset.filter(facility=facility)
            else:
                queryset = queryset.filter(facility__isnull=True)
        return queryset
