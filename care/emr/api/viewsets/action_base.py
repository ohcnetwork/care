from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.action_evaluator.base import ActionEvaluator
from care.emr.models.action import Action
from care.utils.shortcuts import get_object_or_404


class ExecuteAction(BaseModel):
    action: UUID4


class EMRActionBaseViewSet:
    # On save, get all actions and perform it.
    ACTIONS_ENABLED = True
    ACTION_CONTEXT = None
    ACTION_CONTEXT_CLASS = None
    PERFORM_INDEPENDENT_ACTIONS = False

    def get_facility_from_instance(self, instance):
        return None

    def get_additional_actions(self, instance):
        return []

    def perform_actions(self, instance):
        facility = self.get_facility_from_instance(instance)
        actions_list = Action.get_actions_for_context(self.ACTION_CONTEXT, facility)
        extra_actions = self.get_additional_actions(instance)
        all_actions = actions_list + extra_actions
        responses = []
        for actions in all_actions:
            response = ActionEvaluator(
                self.request,
                self.request.user,
                self.ACTION_CONTEXT_CLASS.context_type,
                instance,
                actions,
            ).evaluate()
            responses.append(response)
        return responses

    @extend_schema(
        request=ExecuteAction,
    )
    @action(methods=["POST"], detail=True)
    def execute_action(self, request, *args, **kwargs):
        if not self.PERFORM_INDEPENDENT_ACTIONS:
            raise ValidationError("This action is not performable independently")
        request_params = ExecuteAction(**request.data)
        action = get_object_or_404(
            Action.objects.filter(performable=True, action_context=self.ACTION_CONTEXT),
            external_id=request_params.action,
        )
        instance = self.get_object()
        self.authorize_update(request, instance)
        # TODO: Authorize action permission
        response = ActionEvaluator(
            request,
            request.user,
            self.ACTION_CONTEXT_CLASS.context_type,
            instance,
            action.actions,
        ).evaluate()
        return Response(response)
