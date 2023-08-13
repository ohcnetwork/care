import enum
import json

import requests
from django.conf import settings
from django.core.cache import cache
from rest_framework.exceptions import APIException

from care.facility.models.notification import Notification
from care.users.models import User
from care.utils.jwks.token_generator import generate_jwt


class BaseAssetIntegration:
    auth_header_type = "Care_Bearer "

    class BaseAssetActions(enum.Enum):
        UNLOCK_ASSET = "unlock_asset"
        LOCK_ASSET = "lock_asset"

    def __init__(self, meta):
        self.meta = meta
        self.host = self.meta["local_ip_address"]
        self.middleware_hostname = self.meta["middleware_hostname"]
        self.insecure_connection = self.meta.get("insecure_connection", False)

    def handle_action(self, action):
        pass

    def get_url(self, endpoint):
        protocol = "http"
        if not self.insecure_connection or settings.IS_PRODUCTION:
            protocol += "s"
        return f"{protocol}://{self.middleware_hostname}/{endpoint}"

    def api_post(self, url, data=None):
        req = requests.post(
            url,
            json=data,
            headers={"Authorization": (self.auth_header_type + generate_jwt())},
        )
        try:
            response = req.json()
            if req.status_code >= 400:
                raise APIException(response, req.status_code)
            return response
        except json.decoder.JSONDecodeError:
            return {"error": "Invalid Response"}

    def api_get(self, url, data=None):
        req = requests.get(
            url,
            params=data,
            headers={"Authorization": (self.auth_header_type + generate_jwt())},
        )
        try:
            if req.status_code >= 400:
                raise APIException(req.text, req.status_code)
            response = req.json()
            return response
        except json.decoder.JSONDecodeError:
            return {"error": "Invalid Response"}

    def validate_action(self, action):
        pass

    def generate_notification(self, asset_id, username):
        from care.facility.models.asset import Asset
        from care.utils.notification_handler import NotificationGenerator

        class NotificationGeneratorForAsset(NotificationGenerator):
            def __init__(self, event_type, event, caused_by, caused_object, facility):
                super().__init__(
                    event_type=event_type,
                    event=event,
                    caused_by=caused_by,
                    caused_object=caused_object,
                    facility=facility,
                )

            def generate_system_users(self):
                asset_queue_key = f"waiting_queue_{asset_id}"
                if cache.get(asset_queue_key) is None:
                    return []
                else:
                    queue = cache.get(asset_queue_key)
                    users_array = []
                    for user in queue:
                        users_array.append(User.objects.get(username=user))
                    return users_array

        asset: Asset = Asset.objects.get(external_id=asset_id)

        NotificationGeneratorForAsset(
            event_type=Notification.EventType.CUSTOM_MESSAGE,
            event=Notification.Event.ASSET_UNLOCKED,
            caused_by=User.objects.get(username=username),
            caused_object=asset,
            facility=asset.current_location.facility,
        ).generate()

    def add_to_waiting_queue(self, username, asset_id):
        asset_queue_key = f"waiting_queue_{asset_id}"
        if cache.get(asset_queue_key) is None:
            cache.set(asset_queue_key, [username], timeout=None)
        else:
            queue = cache.get(asset_queue_key)
            if username not in queue:
                queue.append(username)
                cache.set(asset_queue_key, queue, timeout=None)

    def remove_from_waiting_queue(self, username, asset_id):
        asset_queue_key = f"waiting_queue_{asset_id}"
        if cache.get(asset_queue_key) is None:
            return
        else:
            queue = cache.get(asset_queue_key)
            if username in queue:
                queue = [x for x in queue if x != username]
            cache.set(asset_queue_key, queue, timeout=None)

    def unlock_asset(self, username, asset_id):
        if cache.get(asset_id) is None:
            self.remove_from_waiting_queue(username, asset_id)
            self.generate_notification(asset_id, username)
            return True
        elif cache.get(asset_id) == username:
            cache.delete(asset_id)
            self.remove_from_waiting_queue(username, asset_id)
            self.generate_notification(asset_id, username)
            return True
        elif cache.get(asset_id) != username:
            self.remove_from_waiting_queue(username, asset_id)
            return False
        return True

    def lock_asset(self, username, asset_id):
        if cache.get(asset_id) is None or not cache.get(asset_id):
            cache.set(asset_id, username, timeout=None)
            self.remove_from_waiting_queue(username, asset_id)
            return True
        elif cache.get(asset_id) == username:
            self.remove_from_waiting_queue(username, asset_id)
            return True
        self.add_to_waiting_queue(username, asset_id)
        return False

    def verify_access(self, username, asset_id):
        if cache.get(asset_id) is None or cache.get(asset_id) == username:
            return True
        elif cache.get(asset_id) != username:
            return False
        return True
