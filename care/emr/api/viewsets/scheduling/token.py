from django.db import transaction
from django_filters import FilterSet, UUIDFilter
from django_filters.rest_framework import DjangoFilterBackend
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.filters import OrderingFilter

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.models.scheduling.token import Token, TokenQueue, TokenSubQueue
from care.emr.resources.scheduling.token.spec import (
    TokenGenerateSpec,
    TokenReadSpec,
    TokenRetrieveSpec,
    TokenStatusOptions,
    TokenUpdateSpec,
)
from care.facility.models import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.filters.multiselect import MultiSelectFilter
from care.utils.filters.null_filter import NullFilter
from care.utils.lock import Lock
from care.utils.shortcuts import get_object_or_404


class SetCurrentTokenRequest(BaseModel):
    sub_queue: UUID4


class TokenFilters(FilterSet):
    category = UUIDFilter(field_name="category__external_id")
    sub_queue = UUIDFilter(field_name="sub_queue__external_id")
    status = MultiSelectFilter(field_name="status")
    sub_queue_is_null = NullFilter(field_name="sub_queue")


class TokenViewSet(EMRModelViewSet):
    database_model = Token
    pydantic_model = TokenGenerateSpec
    pydantic_update_model = TokenUpdateSpec
    pydantic_read_model = TokenReadSpec
    pydantic_retrieve_model = TokenRetrieveSpec
    filterset_class = TokenFilters
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["created_date", "number"]
    CREATE_QUESTIONNAIRE_RESPONSE = False

    def get_facility_obj(self):
        return get_object_or_404(
            Facility, external_id=self.kwargs["facility_external_id"]
        )

    def get_queue_obj(self):
        facility = self.get_facility_obj()
        return facility, get_object_or_404(
            TokenQueue,
            external_id=self.kwargs["token_queue_external_id"],
            facility=facility,
        )

    def perform_create(self, instance):
        _, queue = self.get_queue_obj()
        instance.queue = queue
        instance.facility = queue.facility
        if queue.facility != instance.category.facility:
            raise ValidationError("Category and Queue are not in the same facility")
        if instance.sub_queue and instance.sub_queue.facility != queue.facility:
            raise ValidationError("Sub Queue and Queue are not in the same facility")
        with Lock(f"booking:token:{queue.id}"), transaction.atomic():
            instance.number = (
                Token.objects.filter(queue=queue, category=instance.category).count()
                + 1
            )
            instance.status = TokenStatusOptions.CREATED.value
            super().perform_create(instance)

    def validate_data(self, instance, model_obj=None):
        if (
            model_obj
            and instance.sub_queue
            and model_obj.sub_queue
            and instance.sub_queue != model_obj.sub_queue.external_id
        ):
            existing_current = TokenSubQueue.objects.filter(
                current_token=model_obj
            ).exists()
            if existing_current:
                raise ValidationError("Sub Queue already has a current token")

        return super().validate_data(instance, model_obj)

    def perform_update(self, instance):
        if instance.sub_queue and instance.sub_queue.facility != instance.facility:
            raise ValidationError("Sub Queue and Queue are not in the same facility")
        with transaction.atomic():
            obj = self.get_object()
            if obj.sub_queue and obj.sub_queue != instance.sub_queue:
                if (
                    instance.sub_queue
                    and obj.sub_queue.resource != instance.sub_queue.resource
                ):
                    raise ValidationError(
                        "Sub Queue and Queue are not in the same resource"
                    )
                # Clear current token if the sub queue is changed
                if obj.sub_queue.current_token == obj:
                    obj.sub_queue.current_token = None
                    obj.sub_queue.save(update_fields=["current_token"])
            super().perform_update(instance)

    def perform_destroy(self, instance):
        instance.status = TokenStatusOptions.ENTERED_IN_ERROR.value
        instance.save()
        return super().perform_destroy(instance)

    def authorize_create(self, instance):
        _, queue = self.get_queue_obj()
        resource = queue.resource
        if not AuthorizationController.call(
            "can_write_token",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create token queue")

    def authorize_update(self, request_obj, model_instance):
        self.authorize_create(model_instance)

    def authorize_destroy(self, instance):
        self.authorize_destroy(instance)

    def authorize_retrieve(self, model_instance):
        _, queue = self.get_queue_obj()
        resource = queue.resource
        if not AuthorizationController.call(
            "can_list_token",
            resource,
            self.request.user,
        ):
            raise PermissionDenied("You do not have permission to create token queue")

    def get_queryset(self):
        _, queue = self.get_queue_obj()
        queryset = (
            super()
            .get_queryset()
            .select_related("created_by", "updated_by")
            .order_by("-modified_date")
        )
        if self.action == "list":
            if not AuthorizationController.call(
                "can_list_token",
                queue.resource,
                self.request.user,
            ):
                raise PermissionDenied(
                    "You do not have permission to create token queue"
                )
            queryset = queryset.filter(queue=queue)
        return queryset

    @action(detail=True, methods=["POST"])
    def set_next(self, request, *args, **kwargs):
        obj = self.get_object()
        request_obj = SetCurrentTokenRequest(**request.data)
        queue = obj.queue
        self.authorize_update(None, None)
        with transaction.atomic():
            sub_queue = get_object_or_404(
                TokenSubQueue,
                external_id=request_obj.sub_queue,
                resource=queue.resource,
            )
            sub_queue.current_token = obj
            sub_queue.save()
            obj.status = TokenStatusOptions.IN_PROGRESS.value
            obj.save()
        return self.get_retrieve_pydantic_model().serialize(obj).to_json()
