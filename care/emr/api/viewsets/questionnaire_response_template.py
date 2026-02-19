from django.db.models import Q
from django_filters import rest_framework as filters
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.organization import FacilityOrganization, FacilityOrganizationUser
from care.emr.models.questionnaire import QuestionnaireResponseTemplate
from care.emr.resources.questionnaire_response_template.spec import (
    QuestionnaireResponseTemplateCreateSpec,
    QuestionnaireResponseTemplateReadSpec,
    QuestionnaireResponseTemplateRetrieveSpec,
    QuestionnaireResponseTemplateUpdateSpec,
)
from care.facility.models import Facility
from care.security.authorization import AuthorizationController
from care.users.models import User
from care.utils.shortcuts import get_object_or_404


class KeyFilter(filters.CharFilter):
    def filter(self, qs, value):
        queryset = qs
        if not value:
            return queryset
        return queryset.filter(available_keys__overlap=[value])


class QuestionnaireTemplateFilters(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains")
    questionnaire = filters.CharFilter(
        lookup_expr="exact", field_name="questionnaire__slug"
    )
    key_filter = KeyFilter()
    facility = filters.UUIDFilter(field_name="facility__external_id")


class QuestionnaireResponseTemplateViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
    EMRDestroyMixin,
):
    database_model = QuestionnaireResponseTemplate
    pydantic_model = QuestionnaireResponseTemplateCreateSpec
    pydantic_update_model = QuestionnaireResponseTemplateUpdateSpec
    pydantic_read_model = QuestionnaireResponseTemplateReadSpec
    pydantic_retrieve_model = QuestionnaireResponseTemplateRetrieveSpec
    filterset_class = QuestionnaireTemplateFilters
    filter_backends = [filters.DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "modified_date"]

    def validate_data(self, instance, model_obj=None):
        users = []
        facility_organizations = []
        facility = None
        if model_obj:
            facility = model_obj.facility
        elif instance.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
        for user in instance.users:
            user_obj = get_object_or_404(User.objects.only("id"), username=user)
            if not user_obj:
                raise ValidationError("User not found")
            users.append(user_obj.id)
        if facility:
            for organization in instance.facility_organizations:
                organization_obj = get_object_or_404(
                    FacilityOrganization.objects.only("id").filter(facility=facility),
                    external_id=organization,
                )
                if not organization:
                    raise ValidationError("Facility organization not found")
                facility_organizations.append(organization_obj.id)
        instance.users = users
        instance.facility_organizations = facility_organizations
        return super().validate_data(instance, model_obj)

    def authorize_create(self, instance):
        """
        The user must have permission to create specimen definition in the facility.
        """
        facility = None
        if instance.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
        if not AuthorizationController.call(
            "can_write_questionnaire_response_template",
            self.request.user,
            facility,
        ):
            raise PermissionDenied("Access Denied to Questionnaire Response Template")

    def authorize_update(self, request_obj, model_instance):
        if not AuthorizationController.call(
            "can_write_questionnaire_response_template",
            self.request.user,
            model_instance.facility,
        ):
            raise PermissionDenied("Access Denied to Questionnaire Response Template")

    def get_queryset(self):
        base_queryset = super().get_queryset()
        user_organization_ids = list(
            FacilityOrganizationUser.objects.filter(user=self.request.user).values_list(
                "organization_id", flat=True
            )
        )
        return base_queryset.filter(
            Q(created_by=self.request.user)
            | Q(users__overlap=[self.request.user.id])
            | Q(facility_organizations__overlap=user_organization_ids)
        )
