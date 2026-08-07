"""
Public asset delivery for facility cover images and user avatars.

ADR-0001: a client never receives a storage-provider URL. These two objects were
already world-readable directly from the bucket, so the routes stay
unauthenticated — who can see the image is unchanged. What changes is that CARE
serves the bytes, which lets the bucket become private and keeps the provider
interchangeable.

They are separate views rather than actions on FacilityViewSet / UserViewSet
because those viewsets filter their querysets by ``request.user`` and cannot
serve an anonymous request.
"""

from django.core.files.storage import storages
from rest_framework.exceptions import NotFound
from rest_framework.views import APIView

from care.emr.utils.file_download import storage_file_response
from care.facility.models.facility import Facility
from care.users.models import User
from care.utils.file_uploads.cover_image import STORAGE_ALIAS
from care.utils.shortcuts import get_object_or_404


class PublicAssetView(APIView):
    """Unauthenticated read-only delivery of a public image."""

    authentication_classes = ()
    permission_classes = ()

    @staticmethod
    def serve(object_key: str | None):
        if not object_key:
            msg = "No image set"
            raise NotFound(msg)
        return storage_file_response(
            storages[STORAGE_ALIAS],
            object_key,
            filename=object_key.rsplit("/", 1)[-1],
        )


class FacilityCoverImageView(PublicAssetView):
    def get(self, request, external_id):
        facility = get_object_or_404(Facility, external_id=external_id)
        return self.serve(facility.cover_image_url)


class UserProfilePictureView(PublicAssetView):
    def get(self, request, username):
        user = get_object_or_404(User, username=username, deleted=False)
        return self.serve(user.profile_picture_url)
