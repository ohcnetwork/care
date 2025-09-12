from django.db import transaction
from django.db.models import Count
from django_filters import CharFilter, DateFilter, FilterSet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.api.viewsets.scheduling.schedule import get_or_create_resource
from care.emr.models.patient import Patient
from care.emr.models.scheduling.token import (
    Token,
    TokenCategory,
    TokenQueue,
    TokenSubQueue,
)
from care.emr.resources.scheduling.token.spec import (
    TokenGenerateWithQueueSpec,
    TokenReadSpec,
    TokenStatusOptions,
)
from care.emr.resources.scheduling.token_queue.spec import (
    TokenQueueCreateSpec,
    TokenQueueReadSpec,
    TokenQueueUpdateSpec,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.lock import Lock
from care.utils.shortcuts import get_object_or_404


class TokenQueueFilters(FilterSet):
    name = CharFilter(field_name="name", lookup_expr="icontains")
    date = DateFilter(field_name="date")
    status = CharFilter(field_name="status", lookup_expr="iexact")


class SubQueueNextTokenRequest(BaseModel):
    sub_queue: UUID4
    category: UUID4 | None = None


class TokenQueueViewSet(EMRModelViewSet):
    database_model = TokenQueue
    pydantic_model = TokenQueueCreateSpec
    pydantic_update_model = TokenQueueUpdateSpec
    pydantic_read_model = TokenQueueReadSpec
    filterset_class = TokenQueueFilters
    filter_backends = [DjangoFilterBackend]
    CREATE_QUESTIONNAIRE_RESPONSE = False

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def perform_create(self, instance):
        facility = self.get_facility_obj()
        with transaction.atomic():
            instance.facility = facility
            resource = get_or_create_resource(
                instance._resource_type,  # noqa SLF001
                instance._resource_id,  # noqa SLF001
                facility,
            )
            instance.resource = resource
            if not TokenQueue.objects.filter(
                resource=resource, date=instance.date
            ).exists():
                instance.is_primary = True
            else:
                instance.is_primary = False
            super().perform_create(instance)

    def authorize_create(self, instance):
        facility = self.get_facility_obj()
        resource = get_or_create_resource(
            instance.resource_type, instance.resource_id, facility
        )
        if not AuthorizationController.call(
            "can_write_token",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create token queue")

    def authorize_update(self, request_obj, model_instance):
        resource = model_instance.resource
        if not AuthorizationController.call(
            "can_write_token",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create token queue")

    def authorize_destroy(self, instance):
        self.authorize_update({}, instance)

    def clean_create_data(self, request_data):
        request_data["facility"] = self.kwargs["facility_external_id"]
        return request_data

    def can_read_resource_token(self, resource_obj):
        if not AuthorizationController.call(
            "can_list_token",
            resource_obj,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to list token queue")

    def authorize_retrieve(self, model_instance):
        resource_obj = model_instance.resource
        self.can_read_resource_token(resource_obj)

    def get_queryset(self):
        facility = self.get_facility_obj()
        queryset = (
            super()
            .get_queryset()
            .select_related("resource", "created_by", "updated_by")
            .order_by("-modified_date")
        )
        if self.action == "list":
            if (
                "resource_type" not in self.request.query_params
                or "resource_id" not in self.request.query_params
            ):
                raise ValidationError("resource_type and resource_id is required")
            resource = get_or_create_resource(
                self.request.query_params["resource_type"],
                self.request.query_params.get("resource_id"),
                facility,
            )
            self.can_read_resource_token(resource)
            queryset = queryset.filter(resource=resource)
        return queryset

    @action(detail=True, methods=["POST"])
    def set_primary(self, request, *args, **kwargs):
        obj = self.get_object()
        self.authorize_update(None, obj)
        with Lock(f"queue:primary:{obj.id}"), transaction.atomic():
            TokenQueue.objects.filter(resource=obj.resource, date=obj.date).update(
                is_primary=False
            )
            obj.is_primary = True
            obj.save()
        return Response(self.get_retrieve_pydantic_model().serialize(obj).to_json())

    @extend_schema(
        request=TokenGenerateWithQueueSpec,
    )
    @action(detail=False, methods=["POST"])
    def generate_token(self, request, *args, **kwargs):
        facility = self.get_facility_obj()
        request_data = TokenGenerateWithQueueSpec(**request.data)
        resource_type = request_data.resource_type
        resource_id = request_data.resource_id
        resource = get_or_create_resource(resource_type, resource_id, facility)
        if not AuthorizationController.call(
            "can_write_token",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create token queue")
        filter_data = {
            "facility": facility,
            "resource": resource,
            "date": request_data.date,
            "is_primary": True,
        }
        queue = TokenQueue.objects.filter(**filter_data).first()
        if not queue:
            filter_data["name"] = "System Generated"
            filter_data["system_generated"] = True
            queue = TokenQueue.objects.create(**filter_data)
        with Lock(f"booking:token:{queue.id}"), transaction.atomic():
            category = get_object_or_404(
                TokenCategory.objects.only("id"),
                facility=facility,
                external_id=request_data.category,
            )
            patient = None
            if request_data.patient:
                patient = get_object_or_404(
                    Patient.objects.only("id"), external_id=request_data.patient
                )
            number = Token.objects.filter(queue=queue, category=category).count() + 1
            token = Token.objects.create(
                facility=facility,
                queue=queue,
                patient=patient,
                category=category,
                number=number,
                status=TokenStatusOptions.CREATED.value,
                note=request_data.note,
            )
        return Response(TokenReadSpec.serialize(token).to_json())

    @extend_schema(
        request=SubQueueNextTokenRequest,
    )
    @action(detail=True, methods=["POST"])
    def set_next_token_to_subqueue(self, request, *args, **kwargs):
        obj = self.get_object()
        self.authorize_update(None, obj)
        request_data = SubQueueNextTokenRequest(**request.data)
        sub_queue = get_object_or_404(
            TokenSubQueue,
            external_id=request_data.sub_queue,
            resource=obj.resource,
        )
        category = None
        if request_data.category:
            category = get_object_or_404(
                TokenCategory,
                facility=obj.facility,
                external_id=request_data.category,
            )
        with Lock(f"queue:next_token:{obj.id}"), transaction.atomic():
            tokens_qs = Token.objects.filter(
                queue=obj, status__in=[TokenStatusOptions.CREATED.value]
            ).order_by("created_date")
            if category:
                tokens_qs = tokens_qs.filter(category=category)
            if tokens_qs.exists():
                next_token = tokens_qs.first()
            else:
                raise ValidationError("No tokens found")
            sub_queue.current_token = next_token
            sub_queue.save()
            next_token.status = TokenStatusOptions.IN_PROGRESS.value
            next_token.sub_queue = sub_queue
            next_token.save()
        return Response(TokenReadSpec.serialize(next_token).to_json())

    @action(detail=True, methods=["GET"])
    def summary(self, request, *args, **kwargs):
        obj = self.get_object()
        self.authorize_retrieve(obj)

        tokens_summary = (
            Token.objects.filter(queue=obj)
            .values("category__name", "status")
            .annotate(count=Count("id"))
            .order_by("category__name", "status")
        )

        summary = {}

        for item in tokens_summary:
            category_name = item["category__name"]
            status = item["status"]
            count = item["count"]

            if category_name not in summary:
                summary[category_name] = {}

            summary[category_name][status] = count

        return Response(summary)
