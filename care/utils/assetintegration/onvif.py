import enum

from rest_framework.exceptions import ValidationError

from care.utils.assetintegration.base import BaseAssetIntegration


class OnvifAsset(BaseAssetIntegration):
    _name = "onvif"

    class OnvifActions(enum.Enum):
        GET_CAMERA_STATUS = "get_status"
        GET_PRESETS = "get_presets"
        GOTO_PRESET = "goto_preset"
        ABSOLUTE_MOVE = "absolute_move"
        RELATIVE_MOVE = "relative_move"

    def __init__(self, meta):
        try:
            super().__init__(meta)
            self.username = self.meta["camera_access_key"].split(":")[0]
            self.password = self.meta["camera_access_key"].split(":")[1]
            self.access_key = self.meta["camera_access_key"].split(":")[2]
        except KeyError as e:
            raise ValidationError(
                dict((key, f"{key} not found in asset metadata") for key in e.args)
            )

    def handle_action(self, action):
        action_type = action["type"]
        action_data = action.get("data", {})
        allowed_action_data = ["x", "y", "zoom"]
        action_data = {
            key: action_data[key] for key in action_data if key in allowed_action_data
        }
        request_body = {
            "hostname": self.host,
            "port": 80,
            "username": self.username,
            "password": self.password,
            "accessKey": self.access_key,
            **action_data,
        }

        if action_type == self.OnvifActions.GET_CAMERA_STATUS.value:
            return self.api_get(self.get_url("status"), request_body)

        if action_type == self.OnvifActions.GET_PRESETS.value:
            return self.api_get(self.get_url("presets"), request_body)

        if action_type == self.OnvifActions.GOTO_PRESET.value:
            return self.api_post(self.get_url("gotoPreset"), request_body)

        if action_type == self.OnvifActions.ABSOLUTE_MOVE.value:
            return self.api_post(self.get_url("absoluteMove"), request_body)

        if action_type == self.OnvifActions.RELATIVE_MOVE.value:
            return self.api_post(self.get_url("relativeMove"), request_body)

        raise ValidationError({"action": "invalid action type"})

    def validate_action(self, action):
        from care.facility.models.bed import AssetBed

        action_type = action["type"]
        action_data = action.get("data", {})
        boundary_preset_id = action_data.get("id", None)

        if (
            not boundary_preset_id
            or action_type != self.OnvifActions.RELATIVE_MOVE.value
        ):
            return

        boundary_preset = AssetBed.objects.filter(
            external_id=boundary_preset_id
        ).first()

        if (
            not boundary_preset
            or not action_data.get("camera_state", None)
            or not action_data["camera_state"].get("x", None)
            or not action_data["camera_state"].get("y", None)
        ):
            raise ValidationError({"action": "invalid action type"})

        boundary_range = boundary_preset.meta.get("range", None)
        camera_state = action_data["camera_state"]

        if (
            (camera_state["x"] + action_data["x"] < boundary_range["min_x"])
            or (camera_state["x"] + action_data["x"] > boundary_range["max_x"])
            or (camera_state["y"] + action_data["y"] < boundary_range["min_y"])
            or (camera_state["y"] + action_data["y"] > boundary_range["max_y"])
        ):
            raise ValidationError({"action": "invalid action type"})

        return
