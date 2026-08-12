from care.action_evaluator.base import ActionEvaluator
from care.emr.models.action import Action


class EMRActionBaseViewSet:
    # On save, get all actions and perform it.
    ACTIONS_ENABLED = True
    ACTION_CONTEXT = None
    ACTION_CONTEXT_CLASS = None

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
