from datetime import UTC, datetime

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response


class HeartbeatView(GenericAPIView):
    permission_classes = ()
    authentication_classes = ()

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "timestamp": str(
                    datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                ),
                "status": "UP",
                "error": None,
            },
            status=status.HTTP_200_OK,
        )
