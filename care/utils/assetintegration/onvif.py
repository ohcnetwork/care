import enum
import json

from django.core.cache import cache
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.users.models import User
from care.utils.assetintegration.base import BaseAssetIntegration


class OnvifAsset(BaseAssetIntegration):
    _name = "onvif"

    class UsageManager:
        def __init__(self, asset_id: str, user: User):
            self.asset = str(asset_id)
            self.user = user
            self.waiting_list_cache_key = f"onvif_waiting_list_{asset_id}"
            self.current_user_cache_key = f"onvif_current_user_{asset_id}"

        def get_waiting_list(self) -> list[User]:
            asset_queue = cache.get(self.waiting_list_cache_key)

            if asset_queue is None:
                return []

            return [
                user
                for username in asset_queue
                if (user := User.objects.filter(username=username).first()) is not None
            ]

        def add_to_waiting_list(self) -> int:
            asset_queue = cache.get(self.waiting_list_cache_key)

            if asset_queue is None:
                asset_queue = []

            if self.user.username not in asset_queue:
                asset_queue.append(self.user.username)
                cache.set(self.waiting_list_cache_key, asset_queue)

            return len(asset_queue)

        def remove_from_waiting_list(self) -> None:
            asset_queue = cache.get(self.waiting_list_cache_key)

            if asset_queue is None:
                asset_queue = []

            if self.user.username in asset_queue:
                asset_queue.remove(self.user.username)
                cache.set(self.waiting_list_cache_key, asset_queue)

        def clear_waiting_list(self) -> None:
            cache.delete(self.waiting_list_cache_key)

        def current_user(self) -> dict:
            from care.facility.api.serializers.asset import UserBaseMinimumSerializer

            current_user = cache.get(self.current_user_cache_key)

            if current_user is None:
                return None

            user = User.objects.filter(username=current_user).first()

            if user is None:
                cache.delete(self.current_user_cache_key)
                return None

            return UserBaseMinimumSerializer(user).data

        def has_access(self) -> bool:
            current_user = cache.get(self.current_user_cache_key)
            return current_user is None or current_user == self.user.username

        def notify_waiting_list_on_asset_availabe(self) -> None:
            from care.utils.notification_handler import send_webpush

            message = json.dumps(
                {
                    "type": "MESSAGE",
                    "asset_id": self.asset,
                    "message": "Camera is now available",
                    "action": "CAMERA_AVAILABILITY",
                }
            )

            for user in self.get_waiting_list():
                send_webpush(username=user.username, message=message)

        def notify_current_user_on_request_access(self) -> None:
            from care.utils.notification_handler import send_webpush

            current_user = cache.get(self.current_user_cache_key)

            if current_user is None:
                return

            requester = User.objects.filter(username=self.user.username).first()

            if requester is None:
                return

            message = json.dumps(
                {
                    "type": "MESSAGE",
                    "asset_id": self.asset,
                    "message": f"{User.REVERSE_TYPE_MAP[requester.user_type]}, {requester.full_name} ({requester.username}) has requested access to the camera",
                    "action": "CAMERA_ACCESS_REQUEST",
                }
            )

            send_webpush(username=current_user, message=message)

        def lock_camera(self) -> bool:
            current_user = cache.get(self.current_user_cache_key)

            if current_user is None or current_user == self.user.username:
                cache.set(self.current_user_cache_key, self.user.username)
                self.remove_from_waiting_list()
                return True

            self.add_to_waiting_list()
            return False

        def unlock_camera(self) -> None:
            current_user = cache.get(self.current_user_cache_key)

            if current_user == self.user.username:
                cache.delete(self.current_user_cache_key)
                self.notify_waiting_list_on_asset_availabe()

            self.remove_from_waiting_list()

        def request_access(self) -> bool:
            if self.lock_camera():
                return True

            self.notify_current_user_on_request_access()
            return False

        def take_control(self):
            pass

    class OnvifActions(enum.Enum):
        GET_CAMERA_STATUS = "get_status"
        GET_PRESETS = "get_presets"
        GOTO_PRESET = "goto_preset"
        ABSOLUTE_MOVE = "absolute_move"
        RELATIVE_MOVE = "relative_move"
        GET_STREAM_TOKEN = "get_stream_token"

        LOCK_CAMERA = "lock_camera"
        UNLOCK_CAMERA = "unlock_camera"
        REQUEST_ACCESS = "request_access"
        TAKE_CONTROL = "take_control"

    def __init__(self, meta):
        try:
            super().__init__(meta)
            self.username = self.meta["camera_access_key"].split(":")[0]
            self.password = self.meta["camera_access_key"].split(":")[1]
            self.access_key = self.meta["camera_access_key"].split(":")[2]
        except KeyError as e:
            raise ValidationError(
                {key: f"{key} not found in asset metadata" for key in e.args}
            ) from e

    def handle_action(self, action, user):  # noqa: PLR0911
        action_type = action["type"]
        action_data = action.get("data", {})
        camera_manager = self.UsageManager(self.id, user)

        request_body = {
            "hostname": self.host,
            "port": 80,
            "username": self.username,
            "password": self.password,
            "accessKey": self.access_key,
            **action_data,
        }

        if action_type == self.OnvifActions.LOCK_CAMERA.value:
            if camera_manager.lock_camera():
                return {
                    "message": "You now have access to the camera controls, the camera is locked for other users",
                    "camera_user": camera_manager.current_user(),
                }

            raise PermissionDenied(
                {
                    "message": "Camera is currently in used by another user, you have been added to the waiting list for camera controls access",
                    "camera_user": camera_manager.current_user(),
                }
            )

        if action_type == self.OnvifActions.UNLOCK_CAMERA.value:
            camera_manager.unlock_camera()
            return {"message": "Camera controls unlocked"}

        if action_type == self.OnvifActions.REQUEST_ACCESS.value:
            if camera_manager.request_access():
                return {
                    "message": "Access to camera camera controls granted",
                    "camera_user": camera_manager.current_user(),
                }

            return {
                "message": "Requested access to camera controls, waiting for current user to release",
                "camera_user": camera_manager.current_user(),
            }

        if action_type == self.OnvifActions.GET_STREAM_TOKEN.value:
            return self.api_post(
                self.get_url("api/stream/getToken/videoFeed"),
                {
                    "stream_id": self.access_key,
                },
            )

        if action_type == self.OnvifActions.GET_CAMERA_STATUS.value:
            return self.api_get(self.get_url("status"), request_body)

        if action_type == self.OnvifActions.GET_PRESETS.value:
            return self.api_get(self.get_url("presets"), request_body)

        if not camera_manager.has_access():
            raise PermissionDenied(
                {
                    "message": "Camera is currently in used by another user, you have been added to the waiting list for camera controls access",
                    "camera_user": camera_manager.current_user(),
                }
            )

        if action_type == self.OnvifActions.GOTO_PRESET.value:
            return self.api_post(self.get_url("gotoPreset"), request_body)

        if action_type == self.OnvifActions.ABSOLUTE_MOVE.value:
            return self.api_post(self.get_url("absoluteMove"), request_body)

        if action_type == self.OnvifActions.RELATIVE_MOVE.value:
            return self.api_post(self.get_url("relativeMove"), request_body)

        raise ValidationError({"action": "invalid action type"})
