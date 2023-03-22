import hashlib

from django.conf import settings
from livekit import AccessToken, VideoGrant
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet


def generate_room_code(source_user, target_user):
    combined = "".join(sorted([source_user, target_user]))
    hash_object = hashlib.sha256(combined.encode("utf-8"))
    hash_hex = hash_object.hexdigest()
    return settings.LIVEKIT_ROOM_NAME_PREFIX + hash_hex


class LiveKitViewSet(
    GenericViewSet,
):
    # permission_classes = (IsAuthenticated,)

    @action(detail=False, methods=["POST"])
    def get_token(self, request):
        source_username = request.data.get("source")
        target_username = request.data.get("target")

        if not source_username or not target_username:
            raise ValidationError("source_username and target_username are required")

        room_code = generate_room_code(source_username, target_username)

        grant = VideoGrant(room_join=True, room=room_code)
        access_token = AccessToken(
            settings.LIVEKIT_API_KEY,
            settings.LIVEKIT_API_SECRET,
            grant=grant,
            identity=source_username,
            name=source_username,
        )
        token = access_token.to_jwt()

        return Response({"access": str(token), "room_code": room_code})
