from enum import Enum

from django.conf import settings
from django.db import transaction
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.emr.api.viewsets.base import emr_exception_handler
from care.emr.utils.batch_requests import execute_batch_requests


class ResourceTypeChoices(str, Enum):
    body = "body"
    url = "url"


class ResourcePath(BaseModel):
    reference_id: str
    path: str
    type: ResourceTypeChoices = ResourceTypeChoices.body


class Replacement(BaseModel):
    source_path: ResourcePath
    value_path: ResourcePath


class Request(BaseModel):
    url: str
    method: str
    body: dict = {}
    reference_id: str
    replacements: list[Replacement] = []


class BatchRequest(BaseModel):
    requests: list[Request] = Field(
        ..., min_length=1, max_length=settings.MAX_REQUESTS_PER_BATCH_REQUEST
    )


class HandledError(Exception):
    pass


class UnHandledError(Exception):
    pass


class BatchRequestView(GenericViewSet):
    def get_exception_handler(self):
        return emr_exception_handler

    def validate_replacements(self, requests):
        reference_id_order = {}
        for index, req in enumerate(requests.requests):
            reference_id_order[req.reference_id] = index

        for req in requests.requests:
            current_index = reference_id_order[req.reference_id]
            for replacement in req.replacements:
                source_reference_id = replacement.source_path.reference_id
                if source_reference_id not in reference_id_order:
                    error_msg = (
                        f"Invalid source_path reference_id : {source_reference_id}"
                    )
                    raise ValidationError(error_msg)
                if reference_id_order[source_reference_id] >= current_index:
                    raise ValidationError(
                        "Source request must come before the current request."
                    )

                value_reference_id = replacement.value_path.reference_id
                if value_reference_id != req.reference_id:
                    error_msg = (
                        f"Invalid value_path reference_id : {value_reference_id}"
                    )
                    raise ValidationError(error_msg)

    @extend_schema(
        request=BatchRequest,
    )
    def create(self, request, *args, **kwargs):
        requests = BatchRequest(**request.data)
        self.validate_replacements(requests)
        errored = False
        loop = 0
        data_references = {}
        replacements = []
        for req in requests.requests:
            for replacement in req.replacements:
                replacements.append(replacement)
        try:
            with transaction.atomic():
                responses = execute_batch_requests(
                    request, requests, replacements, data_references
                )
                structured_responses = []
                for response in responses:
                    if response["status_code"] > 299:  # noqa PLR2004
                        errored = True
                    structured_responses.append(
                        {
                            "reference_id": requests.requests[loop].reference_id,
                            "data": response["data"],
                            "status_code": response["status_code"],
                        }
                    )
                    loop += 1
                if errored:
                    raise HandledError
        except HandledError:
            return Response({"results": structured_responses}, status=400)
        except UnHandledError:
            return Response({"results": structured_responses}, status=500)
        return Response({"results": structured_responses})
