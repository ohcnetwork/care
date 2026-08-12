from rest_framework.exceptions import PermissionDenied

from care.emr.api.viewsets.base import (
    EMRBaseViewSet,
    EMRCreateMixin,
    EMRDestroyMixin,
    EMRListMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRUpsertMixin,
)
from care.emr.models.action import Action
from care.emr.resources.action.spec import (
    ActionConfigurationReadSpec,
    ActionConfigurationRetrieveSpec,
    ActionConfigurationUpdateSpec,
    ActionConfigurationWriteSpec,
)


class ActionConfigurationViewSet(
    EMRCreateMixin,
    EMRRetrieveMixin,
    EMRUpdateMixin,
    EMRListMixin,
    EMRDestroyMixin,
    EMRBaseViewSet,
    EMRUpsertMixin,
):
    database_model = Action
    pydantic_model = ActionConfigurationWriteSpec
    pydantic_update_model = ActionConfigurationUpdateSpec
    pydantic_read_model = ActionConfigurationReadSpec
    pydantic_retrieve_model = ActionConfigurationRetrieveSpec

    def authorize_create(self, instance):
        if instance.facility:
            # Authorize with facility
            raise PermissionDenied(
                "You are not authorized to create an action configuration with a facility"
            )
        if not self.request.user.is_superuser:
            raise PermissionDenied(
                "You are not authorized to create an action configuration without a facility"
            )
        return super().authorize_create(instance)

    def authorize_update(self, request_obj, model_instance):
        if model_instance.facility:
            # Authorize with facility
            raise PermissionDenied(
                "You are not authorized to update an action configuration with a facility"
            )
        if not self.request.user.is_superuser:
            raise PermissionDenied(
                "You are not authorized to update an action configuration without a facility"
            )
        return super().authorize_update(request_obj, model_instance)

    def authorize_destroy(self, instance):
        self.authorize_update(None, instance)

    def get_queryset(self):
        return super().get_queryset()
