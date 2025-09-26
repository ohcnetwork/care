import json

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http.response import Http404
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, ValidationError
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as RestFrameworkValidationError
from rest_framework.fields import get_error_detail
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.viewsets import GenericViewSet

from care.emr.models import QuestionnaireResponse
from care.emr.models.base import EMRBaseModel
from care.emr.resources.base import EMRResource
from care.emr.tagging.base import SingleFacilityTagManager
from care.utils.shortcuts import get_object_or_404


def emr_exception_handler(exc, context):
    if isinstance(exc, DjangoValidationError):
        exc = RestFrameworkValidationError(detail={"detail": get_error_detail(exc)[0]})

    if isinstance(exc, ValidationError):
        return Response({"errors": json.loads(exc.json())}, status=400)
    if isinstance(exc, Http404):
        return Response(
            {
                "errors": [
                    {
                        "type": "object_not_found",
                        "msg": exc.args[0] if exc.args else "Object not found",
                    }
                ]
            },
            status=404,
        )
    if isinstance(exc, RestFrameworkValidationError) and getattr(exc, "detail", None):
        if type(exc.detail) is dict:  # noqa SIM102
            if "errors" in exc.detail:
                return Response(exc.detail, status=400)
        if type(exc.detail) is list:
            errors = " , ".join([str(e) for e in exc.detail])
            return Response(
                {"errors": [{"type": "validation_error", "msg": errors}]}, status=400
            )
        return Response(
            {"errors": [{"type": "validation_error", "msg": exc.detail}]}, status=400
        )
    return drf_exception_handler(exc, context)


# class EMRQuestionnaireMixin:
#     @action(detail=False, methods=["GET"])
#     def questionnaire_spec(self, *args, **kwargs):
#         return Response(
#             {"version": "1.0", "questions": self.pydantic_model.as_questionnaire()}
#         )
#
#     @action(detail=False, methods=["GET"])
#     def json_schema_spec(self, *args, **kwargs):
#         return Response(
#             {"version": "1.0", "questions": self.pydantic_model.model_json_schema()}
#         )


class EMRRetrieveMixin:
    def get_serializer_retrieve_context(self):
        return {}

    def authorize_retrieve(self, model_instance):
        pass

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_retrieve(instance)
        data = (
            self.get_retrieve_pydantic_model()
            .serialize(instance, request.user, **self.get_serializer_retrieve_context())
            .to_json()
        )
        return Response(data)


class EMRCreateMixin:
    def perform_create(self, instance):
        instance.created_by = self.request.user
        instance.updated_by = self.request.user
        with transaction.atomic():
            instance.save()
            if getattr(self, "TAGS_ENABLED", False):
                self.perform_set_tags(instance, self.request.data)
            if getattr(self, "CREATE_QUESTIONNAIRE_RESPONSE", False):
                QuestionnaireResponse.objects.create(
                    subject_id=self.fetch_patient_from_instance(instance).external_id,
                    patient=self.fetch_patient_from_instance(instance),
                    encounter=self.fetch_encounter_from_instance(instance),
                    structured_responses={
                        self.questionnaire_type: {
                            "submit_type": "CREATE",
                            "id": str(instance.external_id),
                        }
                    },
                    structured_response_type=self.questionnaire_type,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )

    def clean_create_data(self, request_data):
        return request_data

    def authorize_create(self, instance):
        pass

    def create(self, request, *args, **kwargs):
        return Response(self.handle_create(request.data))

    def get_serializer_create_context(self):
        return {}

    def handle_create(self, request_data):
        clean_data = self.clean_create_data(request_data)
        context = {"is_create": True, **self.get_serializer_create_context()}
        instance = self.pydantic_model.model_validate(
            clean_data,
            context=context,
        )
        instance._context = context  # noqa: SLF001
        self.validate_data(instance, None)
        self.authorize_create(instance)
        model_instance = instance.de_serialize()
        self.perform_create(model_instance)
        return self.get_retrieve_pydantic_model().serialize(model_instance).to_json()


class EMRListMixin:
    def get_serializer_list_context(self):
        return {}

    def serialize_list(self, obj):
        return (
            self.get_read_pydantic_model()
            .serialize(obj, **self.get_serializer_list_context())
            .to_json()
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            data = [self.serialize_list(obj) for obj in page]
            return paginator.get_paginated_response(data)
        data = [self.serialize_list(obj) for obj in queryset]
        return Response(data)


class EMRUpdateMixin:
    def perform_update(self, instance):
        instance.updated_by = self.request.user
        # TODO Handle historical data by taking a dump from current model and appending to history object
        with transaction.atomic():
            instance.save()
            if getattr(self, "CREATE_QUESTIONNAIRE_RESPONSE", False):
                QuestionnaireResponse.objects.create(
                    subject_id=self.fetch_patient_from_instance(instance).external_id,
                    patient=self.fetch_patient_from_instance(instance),
                    encounter=self.fetch_encounter_from_instance(instance),
                    structured_responses={
                        self.questionnaire_type: {
                            "submit_type": "UPDATE",
                            "id": str(instance.external_id),
                        }
                    },
                    structured_response_type=self.questionnaire_type,
                    created_by=self.request.user,
                    updated_by=self.request.user,
                )

    def clean_update_data(self, request_data, keep_fields: set | None = None):
        if type(request_data) is list:
            return request_data
        ignored_fields = {"id", "external_id", "patient", "encounter"}
        if keep_fields:
            ignored_fields = ignored_fields - set(keep_fields)
        if hasattr(request_data, "dict"):
            # convert immutable querydict to dict
            request_data = request_data.dict()
        for field in ignored_fields:
            request_data.pop(field, None)
        return request_data

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self.handle_update(instance, request.data))

    def partial_update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return self.update(request, *args, **kwargs)

    def get_serializer_update_context(self):
        return {}

    def authorize_update(self, request_obj, model_instance):
        pass

    def handle_update(self, instance, request_data):
        clean_data = self.clean_update_data(request_data)  # From Create
        pydantic_model = self.get_update_pydantic_model()
        context = {
            "is_update": True,
            "object": instance,
            **self.get_serializer_update_context(),
        }
        serializer_obj = pydantic_model.model_validate(
            clean_data,
            context=context,
        )
        serializer_obj._context = context  # noqa: SLF001
        self.validate_data(serializer_obj, instance)
        self.authorize_update(serializer_obj, instance)
        partial = getattr(self, "partial", False)
        model_instance = serializer_obj.de_serialize(obj=instance, partial=partial)
        self.perform_update(model_instance)
        return self.get_retrieve_pydantic_model().serialize(model_instance).to_json()


class EMRDestroyMixin:
    def authorize_destroy(self, instance):
        pass

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save(update_fields=["deleted"])

    def validate_destroy(self, instance):
        pass

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.validate_destroy(instance)
        self.authorize_destroy(instance)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class EMRUpsertMixin:
    @action(detail=False, methods=["POST"])
    def upsert(self, request, *args, **kwargs):
        if type(request.data) is not dict:
            raise RestFrameworkValidationError("Invalid request data")
        datapoints = request.data.get("datapoints", [])
        if len(datapoints) == 0:
            raise RestFrameworkValidationError("No datapoints provided")
        if len(datapoints) > settings.MAX_DATAPOINTS_PER_UPSERT:
            raise RestFrameworkValidationError("Too many datapoints provided")
        results = []
        errored = False
        unhandled = False
        try:
            with transaction.atomic():
                for datapoint in datapoints:
                    try:
                        if "id" in datapoint:
                            instance = get_object_or_404(
                                self.database_model,
                                **{self.lookup_field: datapoint["id"]},
                            )
                            result = self.handle_update(instance, datapoint)
                        else:
                            result = self.handle_create(datapoint)
                        results.append(result)
                    except Exception as e:
                        errored = True
                        handler = emr_exception_handler(e, {})
                        if not getattr(handler, "data", None):
                            unhandled = True
                            raise e
                        results.append(handler.data)
                if errored:
                    raise Exception
        except Exception as e:
            if unhandled:
                raise e
            return Response(results, status=400)
        return Response(results)


class EMRBaseViewSet(GenericViewSet):
    pydantic_model: EMRResource = None
    pydantic_read_model: EMRResource = None
    pydantic_update_model: EMRResource = None
    pydantic_retrieve_model: EMRResource = None
    database_model: EMRBaseModel = None
    lookup_field = "external_id"

    def get_exception_handler(self):
        return emr_exception_handler

    def get_queryset(self):
        return self.database_model.objects.all().order_by("-id")

    def get_retrieve_pydantic_model(self):
        if self.pydantic_retrieve_model:
            return self.pydantic_retrieve_model
        return self.get_read_pydantic_model()

    def get_read_pydantic_model(self):
        if self.pydantic_read_model:
            return self.pydantic_read_model
        return self.pydantic_model

    def get_update_pydantic_model(self):
        if self.pydantic_update_model:
            return self.pydantic_update_model
        return self.pydantic_model

    def get_object(self):
        queryset = self.get_queryset()
        return get_object_or_404(
            queryset, **{self.lookup_field: self.kwargs[self.lookup_field]}
        )

    def validate_data(self, instance, model_obj=None):
        pass

    def fetch_encounter_from_instance(self, instance):
        return instance.encounter

    def fetch_patient_from_instance(self, instance):
        return instance.patient


class EMRQuestionnaireResponseMixin:
    CREATE_QUESTIONNAIRE_RESPONSE = True


class TagRequest(BaseModel):
    tags: list[UUID4] = []


class EMRTagMixin:
    resource_type = None
    tag_manager = SingleFacilityTagManager
    TAGS_ENABLED = True

    def get_facility_from_instance(self, instance):
        return instance.facility  # Overide as needed

    def perform_set_tags(self, instance, data):
        tag_request = TagRequest.model_validate(data)
        tag_manager = self.tag_manager()
        try:
            tag_manager.set_tags(
                self.resource_type,
                instance,
                tag_request.tags,
                self.request.user,
                self.get_facility_from_instance(instance),
            )
        except ValueError as e:
            raise RestFrameworkValidationError(str(e)) from e

    @extend_schema(request=TagRequest)
    @action(detail=True, methods=["POST"])
    def set_tags(self, request, *args, **kwargs):
        # TODO Facility AuthZ missing
        if not self.resource_type:
            return Response({})
        instance = self.get_object()
        self.perform_set_tags(instance, request.data)
        return self.retrieve(request, *args, **kwargs)

    @extend_schema(request=TagRequest)
    @action(detail=True, methods=["POST"])
    def remove_tags(self, request, *args, **kwargs):
        # TODO Facility AuthZ missing
        if not self.resource_type:
            return Response({})
        instance = self.get_object()
        tag_request = TagRequest.model_validate(request.data)
        tag_manager = self.tag_manager()
        tag_manager.unset_tags(
            instance,
            tag_request.tags,
            request.user,
        )
        return self.retrieve(request, *args, **kwargs)


class EMRModelViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRDestroyMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    pass


class EMRModelReadOnlyViewSet(
    EMRRetrieveMixin,
    EMRListMixin,
    EMRBaseViewSet,
):
    pass
