from datetime import datetime, timezone

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


class HeartbeatView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = []

    def get(self, request, *args, **kwargs):
        return Response(
            {
                "timestamp": str(
                    datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                ),
                "status": "UP",
                "error": None,
            },
            status=status.HTTP_200_OK,
        )
