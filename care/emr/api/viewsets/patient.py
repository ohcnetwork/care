from django.db import transaction
from django.utils import timezone
from django_filters import CharFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models import Organization, PatientUser, TokenBooking
from care.emr.models.patient import Patient, PatientIdentifier, PatientIdentifierConfig
from care.emr.resources.patient.spec import (
    PatientCreateSpec,
    PatientIdentifierConfigRequest,
    PatientListSpec,
    PatientPartialSpec,
    PatientRetrieveSpec,
    PatientUpdateSpec,
    validate_identifier_config,
)
from care.emr.resources.patient_identifier.default_expression_evaluator import (
    evaluate_patient_instance_default_values,
)
from care.emr.resources.scheduling.slot.spec import TokenBookingReadSpec
from care.emr.resources.tag.config_spec import TagResource
from care.emr.resources.user.spec import UserSpec
from care.emr.tagging.base import PatientFacilityTagManager, PatientInstanceTagManager
from care.facility.models.facility import Facility
from care.security.authorization import AuthorizationController
from care.security.models import RoleModel
from care.users.models import User


class PatientFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    phone_number = CharFilter(field_name="phone_number", lookup_expr="iexact")


class PatientViewSet(EMRModelViewSet):
    database_model = Patient
    pydantic_model = PatientCreateSpec
    pydantic_read_model = PatientListSpec
    pydantic_update_model = PatientUpdateSpec
    pydantic_retrieve_model = PatientRetrieveSpec
    filterset_class = PatientFilters
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_patient_obj", self.request.user, model_instance
        ):
            raise PermissionDenied("Cannot Create Patient")

    def authorize_create(self, request_obj):
        if not AuthorizationController.call("can_create_patient", self.request.user):
            raise PermissionDenied("Cannot Create Patient")

    def authorize_destroy(self, instance):
        if not self.request.user.is_superuser:
            raise PermissionDenied("Cannot delete patient")

    def validate_data(self, instance, model_obj=None):
        dob = instance.date_of_birth or (model_obj and model_obj.date_of_birth)
        deceased = instance.deceased_datetime or (
            model_obj and model_obj.deceased_datetime
        )

        if dob and deceased and dob > deceased.date():
            raise ValidationError("Date of birth cannot be after the date of death")

        age = instance.age or (
            model_obj
            and model_obj.year_of_birth
            and timezone.now().year - model_obj.year_of_birth
        )

        if age and deceased:
            calculated_birth_year = timezone.now().year - age
            if calculated_birth_year > deceased.year:
                raise ValidationError("Year of birth cannot be after the year of death")

    def get_queryset(self):
        qs = (
            super()
            .get_queryset()
            .select_related("created_by", "updated_by", "geo_organization")
        )
        if self.action != "list":
            patient = get_object_or_404(
                Patient, external_id=self.kwargs.get("external_id")
            )
            if AuthorizationController.call(
                "can_view_clinical_data", self.request.user, patient
            ):
                return qs.filter(external_id=self.kwargs.get("external_id"))

        if self.request.GET.get("organization"):
            geo_organization = get_object_or_404(
                Organization,
                external_id=self.request.GET["organization"],
            )
            qs = qs.filter(organization_cache__overlap=[geo_organization.id])
        return AuthorizationController.call(
            "get_filtered_patients", qs, self.request.user
        )

    def perform_create(self, instance):
        identifiers = instance._identifiers  # noqa: SLF001
        # TODO : Lock to one patient create at a time
        with transaction.atomic():
            super().perform_create(instance)
            for identifier in identifiers:
                PatientIdentifier.objects.create(
                    patient=instance,
                    config=get_object_or_404(
                        PatientIdentifierConfig, external_id=identifier.config
                    ),
                    value=identifier.value,
                )
            evaluate_patient_instance_default_values(instance)

            instance.build_instance_identifiers()
            instance.save()
            tag_manager = PatientInstanceTagManager()
            tag_manager.set_tags(
                TagResource.patient,
                instance,
                instance._tags,  # noqa: SLF001
                self.request.user,
            )

    def perform_update(self, instance):
        identifiers = instance._identifiers  # noqa: SLF001
        with transaction.atomic():
            super().perform_update(instance)
            for identifier in identifiers:
                identifier_obj = PatientIdentifier.objects.filter(
                    patient=instance,
                    config=get_object_or_404(
                        PatientIdentifierConfig, external_id=identifier.config
                    ),
                ).first()
                if identifier_obj:
                    if not identifier.value:
                        identifier_obj.delete()
                else:
                    identifier_obj = PatientIdentifier(
                        patient=instance,
                        config=get_object_or_404(
                            PatientIdentifierConfig, external_id=identifier.config
                        ),
                    )
                if identifier.value:
                    identifier_obj.value = identifier.value
                    identifier_obj.save()
            instance.build_instance_identifiers()
            instance.save()

    class SearchRequestSpec(BaseModel):
        phone_number: str | None = None  # Old Identifier
        config: UUID4 | None = None
        value: str | None = None
        facility: UUID4 | None = None

    @extend_schema(
        request=SearchRequestSpec,
    )
    @action(detail=False, methods=["POST"])
    def search(self, request, *args, **kwargs):
        max_page_size = 200
        request_data = self.SearchRequestSpec(**request.data)
        partial = False
        if not request_data.phone_number and not request_data.config:
            raise ValidationError("Either phone number or config is required")
        if request_data.phone_number:
            queryset = Patient.objects.filter(phone_number=request_data.phone_number)
            partial = True
        else:
            config_queryset = PatientIdentifierConfig.objects.filter(
                external_id=request_data.config
            )
            if request_data.facility:
                config_queryset = config_queryset.filter(
                    facility__external_id=request_data.facility
                )
            config = config_queryset.first()
            if not config:
                raise ValidationError("Config not found")

            queryset = PatientIdentifier.objects.filter(
                config=config,
                value__iexact=request_data.value,
            )
            identifier = queryset.first()

            if config.config.get("retrieve_config", {}).get(
                "retrieve_with_year_of_birth"
            ):
                partial = True
            if not identifier:
                queryset = queryset.none()
            else:
                queryset = Patient.objects.filter(id=identifier.patient_id)
        queryset = queryset.order_by("-created_date")[:max_page_size]
        if partial:
            data = [PatientPartialSpec.serialize(obj).to_json() for obj in queryset]
            return Response({"partial": True, "results": data})
        data = [PatientRetrieveSpec.serialize(obj).to_json() for obj in queryset]
        return Response({"partial": False, "results": data})

    class SearchRetrieveRequestSpec(BaseModel):
        phone_number: str
        year_of_birth: int
        partial_id: str

    @extend_schema(
        request=SearchRetrieveRequestSpec, responses={200: PatientRetrieveSpec}
    )
    @action(detail=False, methods=["POST"])
    def search_retrieve(self, request, *args, **kwargs):
        request_data = self.SearchRetrieveRequestSpec(**request.data)
        queryset = Patient.objects.filter(phone_number=request_data.phone_number)
        queryset = queryset.filter(year_of_birth=request_data.year_of_birth)
        for patient in queryset:
            if str(patient.external_id)[:5] == request_data.partial_id:
                return Response(PatientRetrieveSpec.serialize(patient).to_json())
        raise PermissionDenied("No valid patients found")

    @action(detail=True, methods=["GET"])
    def get_users(self, request, *args, **kwargs):
        patient = self.get_object()
        patient_users = PatientUser.objects.filter(patient=patient)
        data = [
            UserSpec.serialize(patient_user.user).to_json()
            for patient_user in patient_users
        ]
        return Response({"results": data})

    class PatientUserCreateSpec(BaseModel):
        user: UUID4
        role: UUID4

    @extend_schema(request=PatientUserCreateSpec, responses={200: UserSpec})
    @action(detail=True, methods=["POST"])
    def add_user(self, request, *args, **kwargs):
        request_data = self.PatientUserCreateSpec(**self.request.data)
        user = get_object_or_404(User, external_id=request_data.user)
        role = get_object_or_404(RoleModel, external_id=request_data.role)
        patient = self.get_object()
        self.authorize_update({}, patient)
        if PatientUser.objects.filter(user=user, patient=patient).exists():
            raise ValidationError("User already exists")
        PatientUser.objects.create(user=user, patient=patient, role=role)
        return Response(UserSpec.serialize(user).to_json())

    class PatientUserDeleteSpec(BaseModel):
        user: UUID4

    @extend_schema(request=PatientUserDeleteSpec, responses={200: {}})
    @action(detail=True, methods=["POST"])
    def delete_user(self, request, *args, **kwargs):
        request_data = self.PatientUserDeleteSpec(**self.request.data)
        user = get_object_or_404(User, external_id=request_data.user)
        patient = self.get_object()
        self.authorize_update({}, patient)
        if not PatientUser.objects.filter(user=user, patient=patient).exists():
            raise ValidationError("User does not exist")
        PatientUser.objects.filter(user=user, patient=patient).delete()
        return Response({})

    @action(detail=True, methods=["GET"])
    def get_appointments(self, request, *args, **kwargs):
        appointments = TokenBooking.objects.filter(patient=self.get_object())
        return Response(
            {
                "results": [
                    TokenBookingReadSpec.serialize(obj).to_json()
                    for obj in appointments
                ]
            }
        )

    @extend_schema(
        request=PatientIdentifierConfigRequest, responses={200: PatientRetrieveSpec}
    )
    @action(detail=True, methods=["POST"])
    def update_identifier(self, request, *args, **kwargs):
        request_data = PatientIdentifierConfigRequest(**self.request.data)
        patient = self.get_object()
        self.authorize_update({}, patient)
        request_config = get_object_or_404(
            PatientIdentifierConfig, external_id=request_data.config
        )
        # TODO: Check Facility Authz
        value = request_data.value
        if not value and request_config.config["required"]:
            raise ValidationError("Value is required")
        if value:
            validate_identifier_config(
                {"config": request_config.config, "id": request_config.external_id},
                value,
            )

        patient_identifier = PatientIdentifier.objects.filter(
            patient=patient, config=request_config
        ).first()
        if patient_identifier and not value:
            patient_identifier.delete()
        if not patient_identifier:
            patient_identifier = PatientIdentifier.objects.create(
                patient=patient, config=request_config, value=value
            )
        patient_identifier.value = value
        if request_config.facility:
            patient_identifier.facility = request_config.facility
        patient_identifier.save()
        if request_config.facility:
            patient.build_facility_identifiers(request_config.facility.id)
        else:
            patient.build_instance_identifiers()
        patient.save()
        # TODO : Retrieve will not send the facility identifiers
        return Response(PatientRetrieveSpec.serialize(patient).to_json())

    class PatientTagRequest(BaseModel):
        tags: list[UUID4]
        facility: UUID4 | None = None

    @extend_schema(request=PatientTagRequest)
    @action(detail=True, methods=["POST"])
    def set_instance_tags(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        tag_request = self.PatientTagRequest.model_validate(request.data)
        tag_manager = PatientInstanceTagManager()
        tag_manager.set_tags(
            TagResource.patient,
            instance,
            tag_request.tags,
            self.request.user,
        )
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(request=PatientTagRequest)
    @action(detail=True, methods=["POST"])
    def remove_instance_tags(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        tag_request = self.PatientTagRequest.model_validate(request.data)
        tag_manager = PatientInstanceTagManager()
        tag_manager.unset_tags(
            instance,
            tag_request.tags,
            request.user,
        )
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(request=PatientTagRequest)
    @action(detail=True, methods=["POST"])
    def set_facility_tags(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        tag_request = self.PatientTagRequest.model_validate(request.data)
        tag_manager = PatientFacilityTagManager(tag_request.facility)
        tag_manager.set_tags(
            TagResource.patient,
            instance,
            tag_request.tags,
            self.request.user,
        )
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(request=PatientTagRequest)
    @action(detail=True, methods=["POST"])
    def remove_facility_tags(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update({}, instance)
        tag_request = self.PatientTagRequest.model_validate(request.data)
        tag_manager = PatientFacilityTagManager(tag_request.facility)
        tag_manager.unset_tags(
            instance,
            tag_request.tags,
            request.user,
        )
        return self.retrieve(request, *args, **kwargs)

    def get_serializer_retrieve_context(self):
        return self.get_serializer_list_context()

    def get_serializer_list_context(self):
        facility = self.request.GET.get("facility", None)
        if facility:
            facility = get_object_or_404(Facility, external_id=facility)
            if not AuthorizationController.call(
                "can_list_facility_tag_config", self.request.user, facility
            ):
                raise PermissionDenied("Cannot view facility tags")
        return {"facility": facility}
