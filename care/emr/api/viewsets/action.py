from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

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
from care.emr.registries.actions.context import ActionContextRegistry
from care.emr.registries.actions.field import ActionFieldRegistry
from care.emr.registries.actions.instruction import ActionInstructionRegistry
from care.emr.resources.action.spec import (
    ActionConfigurationReadSpec,
    ActionConfigurationRetrieveSpec,
    ActionConfigurationUpdateSpec,
    ActionConfigurationWriteSpec,
)

local_cache = {"contexts": {}, "instructions": {}, "fields": {}}


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

    @action(detail=False, methods=["GET"])
    def contexts(self, request, *args, **kwargs):
        if not local_cache["contexts"]:
            local_cache["contexts"] = ActionContextRegistry.render_all_contexts()
        return Response({"contexts": local_cache["contexts"]})

    @action(detail=False, methods=["GET"])
    def instructions(self, request, *args, **kwargs):
        if not local_cache["instructions"]:
            local_cache["instructions"] = (
                ActionInstructionRegistry.render_all_instructions()
            )
        return Response({"instructions": local_cache["instructions"]})

    @action(detail=False, methods=["GET"])
    def fields(self, request, *args, **kwargs):
        if not local_cache["fields"]:
            local_cache["fields"] = ActionFieldRegistry.render_all_fields()
        return Response({"fields": local_cache["fields"]})
