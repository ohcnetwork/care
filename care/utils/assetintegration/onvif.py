import enum

from rest_framework.exceptions import PermissionDenied, ValidationError

from care.utils.assetintegration.base import BaseAssetIntegration
from care.utils.assetintegration.usage_manager import UsageManager


class OnvifAsset(BaseAssetIntegration):
    _name = "onvif"

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
        camera_manager = UsageManager(self.id, user)

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
