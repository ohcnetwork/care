from django.db.models import CharField, Exists, OuterRef
from django.db.models.functions import Cast
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.api.viewsets.condition import ValidateEncounterMixin
from care.emr.api.viewsets.encounter_authz_base import EncounterBasedAuthorizationBase
from care.emr.models import FileUpload
from care.emr.models.consent import Consent
from care.emr.resources.consent.spec import (
    ConsentCreateSpec,
    ConsentListSpec,
    ConsentRetrieveSpec,
    ConsentUpdateSpec,
    ConsentVerificationSpec,
)
from care.emr.resources.file_upload.spec import (
    FileCategoryChoices,
    FileTypeChoices,
)
from care.utils.time_util import care_now


class ConsentFilter(filters.FilterSet):
    attachment_name = filters.CharFilter(
        method="filter_attachment_name", label="Filter by attachment name"
    )

    def filter_attachment_name(self, queryset, name, value):
        if not value:
            return queryset

        # Find consents that have attachments with names containing the search value
        # Cast external_id to string to match the type in associating_id
        queryset = queryset.annotate(external_id_str=Cast("external_id", CharField()))

        # Create a subquery to check for matching file attachments
        attachment_filter = FileUpload.objects.filter(
            associating_id=OuterRef("external_id_str"),
            file_category=FileCategoryChoices.consent_attachment,
            file_type=FileTypeChoices.consent,
            name__icontains=value,
        )

        # Filter the queryset to include only consents with matching attachments
        return queryset.filter(Exists(attachment_filter))

    class Meta:
        model = Consent
        fields = ["attachment_name"]


class ConsentViewSet(
    ValidateEncounterMixin,
    EncounterBasedAuthorizationBase,
    EMRModelViewSet,
):
    database_model = Consent
    pydantic_model = ConsentCreateSpec
    pydantic_read_model = ConsentListSpec
    pydantic_update_model = ConsentUpdateSpec
    pydantic_retrieve_model = ConsentRetrieveSpec
    filterset_class = ConsentFilter
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        self.authorize_read_encounter()
        return (
            super()
            .get_queryset()
            .filter(encounter__patient__external_id=self.kwargs["patient_external_id"])
            .select_related("encounter", "created_by", "updated_by")
        )

    @extend_schema(request=ConsentVerificationSpec)
    @action(detail=True, methods=["POST"])
    def add_verification(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_update(None, instance)
        request_data = ConsentVerificationSpec(**request.data)

        request_data.verified_by = str(self.request.user.external_id)
        request_data.verification_date = care_now().isoformat()

        if request_data.verified_by in [
            verification.get("verified_by")
            for verification in instance.verification_details
        ]:
            raise ValidationError("Consent is already verified by the user")

        instance.verification_details.append(request_data.model_dump())
        instance.save(update_fields=["verification_details"])

        serialized = ConsentRetrieveSpec.serialize(instance).to_json()
        return Response(serialized)

    class VerificationRemovalSchema(BaseModel):
        verified_by: UUID4 | None = None

    @extend_schema(request=VerificationRemovalSchema)
    @action(detail=True, methods=["POST"])
    def remove_verification(self, request, *args, **kwargs):
        instance = self.get_object()
        request_data = self.VerificationRemovalSchema(**request.data)
        self.authorize_update(None, instance)
        if not request_data.verified_by:
            request_data.verified_by = str(self.request.user.external_id)
        match = None
        for verification in instance.verification_details:
            if str(verification.get("verified_by")) == str(request_data.verified_by):
                match = verification
                break

        if not match:
            raise ValidationError("Consent is not verified by the user")

        instance.verification_details.remove(match)
        instance.save(update_fields=["verification_details"])

        serialized = ConsentRetrieveSpec.serialize(instance).to_json()
        return Response(serialized)
