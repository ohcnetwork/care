from django.db import transaction
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.emr.api.viewsets.base import emr_exception_handler
from care.emr.utils.batch_requests import execute_batch_requests


class Request(BaseModel):
    url: str
    method: str
    body: dict = {}
    reference_id: str


class BatchRequest(BaseModel):
    requests: list[Request] = Field(..., min_length=1, max_length=20)


class HandledError(Exception):
    pass


class BatchRequestView(GenericViewSet):
    def get_exception_handler(self):
        return emr_exception_handler

    @extend_schema(
        request=BatchRequest,
    )
    def create(self, request, *args, **kwargs):
        requests = BatchRequest(**request.data)
        errored = False
        loop = 0
        try:
            with transaction.atomic():
                responses = execute_batch_requests(request, requests)
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
        return Response({"results": structured_responses})
