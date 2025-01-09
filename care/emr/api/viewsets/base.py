import json

from django.db import transaction
from django.http.response import Http404
from pydantic import ValidationError
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as RestFrameworkValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.viewsets import GenericViewSet

from care.emr.models import QuestionnaireResponse
from care.emr.models.base import EMRBaseModel
from care.emr.resources.base import EMRResource


def emr_exception_handler(exc, context):
    if isinstance(exc, ValidationError):
        return Response({"errors": json.loads(exc.json())}, status=400)
    if isinstance(exc, Http404):
        return Response(
            {
                "errors": [
                    {
                        "type": "object_not_found",
                        "msg": "Object not found",
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


class EMRQuestionnaireMixin:
    @action(detail=False, methods=["GET"])
    def questionnaire_spec(self, *args, **kwargs):
        return Response(
            {"version": "1.0", "questions": self.pydantic_model.as_questionnaire()}
        )

    @action(detail=False, methods=["GET"])
    def json_schema_spec(self, *args, **kwargs):
        return Response(
            {"version": "1.0", "questions": self.pydantic_model.model_json_schema()}
        )


class EMRRetrieveMixin:
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        data = self.get_retrieve_pydantic_model().serialize(instance, request.user)
        return Response(data.to_json())


class EMRCreateMixin:
    def perform_create(self, instance):
        instance.created_by = self.request.user
        instance.updated_by = self.request.user
        with transaction.atomic():
            instance.save()
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

    def handle_create(self, request_data):
        clean_data = self.clean_create_data(request_data)
        instance = self.pydantic_model(**clean_data)
        self.validate_data(instance, None)
        self.authorize_create(instance)
        model_instance = instance.de_serialize()
        self.perform_create(model_instance)
        return self.get_retrieve_pydantic_model().serialize(model_instance).to_json()


class EMRListMixin:
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            data = [
                self.get_read_pydantic_model().serialize(obj).to_json() for obj in page
            ]
            return paginator.get_paginated_response(data)
        data = [
            self.get_read_pydantic_model().serialize(obj).to_json() for obj in queryset
        ]
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

    def clean_update_data(self, request_data):
        if type(request_data) is list:
            return request_data
        request_data.pop("id", None)
        request_data.pop("external_id", None)
        request_data.pop("patient", None)
        request_data.pop("encounter", None)
        return request_data

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        return Response(self.handle_update(instance, request.data))

    def authorize_update(self, request_obj, model_instance):
        pass

    def handle_update(self, instance, request_data):
        clean_data = self.clean_update_data(request_data)  # From Create
        pydantic_model = self.get_update_pydantic_model()
        serializer_obj = pydantic_model.model_validate(
            clean_data, context={"is_update": True, "object": instance}
        )
        self.validate_data(serializer_obj, instance)
        self.authorize_update(serializer_obj, instance)
        model_instance = serializer_obj.de_serialize(obj=instance)
        self.perform_update(model_instance)
        return self.get_retrieve_pydantic_model().serialize(model_instance).to_json()


class EMRDestroyMixin:
    def authorize_destroy(self, instance):
        pass

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save(update_fields=["deleted"])

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.authorize_destroy(instance)
        self.perform_destroy(instance)
        return Response(status=204)


class EMRUpsertMixin:
    @action(detail=False, methods=["POST"])
    def upsert(self, request, *args, **kwargs):
        datapoints = request.data.get("datapoints", [])
        results = []
        errored = False
        try:
            with transaction.atomic():
                for datapoint in datapoints:
                    try:
                        if "id" in datapoint:
                            instance = get_object_or_404(
                                self.database_model, external_id=datapoint["id"]
                            )
                            result = self.handle_update(instance, datapoint)
                        else:
                            result = self.handle_create(datapoint)
                        results.append(result)
                    except Exception as e:
                        errored = True
                        results.append(emr_exception_handler(e, {}).data)
                if errored:
                    raise Exception
        except Exception:
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
        return self.filter_queryset(self.database_model.objects.all())

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
