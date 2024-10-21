import json

from django.core.cache import cache

from care.users.models import User


class UsageManager:
    def __init__(self, asset_id: str, user: User):
        self.asset = str(asset_id)
        self.user = user
        self.waiting_list_cache_key = f"onvif_waiting_list_{asset_id}"
        self.current_user_cache_key = f"onvif_current_user_{asset_id}"

    def get_waiting_list(self) -> list[User]:
        asset_queue = cache.get(self.waiting_list_cache_key)

        return list(User.objects.filter(username__in=asset_queue or []))

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
