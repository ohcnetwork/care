from pydantic import UUID4, BaseModel, Field
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.action_evaluator.context_engine.contexts.core import (
    EncounterContext,
    PatientContext,
)
from care.action_evaluator.instruction_engine.base import (
    BaseInstruction,
    InstructionType,
)
from care.action_evaluator.instruction_engine.resolvers import (
    resolve_encounter,
    resolve_patient,
)
from care.emr.models.tag_config import TagConfig
from care.emr.registries.actions.instruction import ActionInstructionRegistry
from care.emr.resources.tag.config_spec import TagResource
from care.emr.tagging.base import (
    PatientFacilityTagManager,
    PatientInstanceTagManager,
    SingleFacilityTagManager,
)
from care.security.authorization import AuthorizationController


def _tag_input(resource: str):
    class TagInput(BaseModel):
        tag: UUID4 = Field(
            title="Tag",
            description="Applied when the condition holds; already-set tags are skipped.",
            json_schema_extra={
                "x-care-picker": "tag_config",
                "x-care-resource": resource,
            },
        )

    return TagInput


class TagOutput(BaseModel):
    performed: bool
    tag: str | None = None
    message: str


class BaseTagInstruction(BaseInstruction):
    instruction_type = InstructionType.PERFORMED
    output_schema = TagOutput
    resource: TagResource

    def resolve_target(self):
        raise NotImplementedError

    def tag_manager_for(self, tag_config, target):
        raise NotImplementedError

    def facility_for(self, tag_config, target):
        return tag_config.facility

    def evaluate(self):
        tag_config = TagConfig.objects.filter(external_id=self.inputs["tag"]).first()
        if not tag_config:
            return {"performed": False, "tag": None, "message": "Tag no longer exists"}
        target = self.resolve_target()
        if target is None:
            return {
                "performed": False,
                "tag": tag_config.display,
                "message": f"Nothing to tag with \u201c{tag_config.display}\u201d",
            }
        manager = self.tag_manager_for(tag_config, target)
        try:
            manager.set_tag(
                self.resource.value,
                target,
                tag_config.external_id,
                self.user,
                self.facility_for(tag_config, target),
            )
        except (ValidationError, PermissionDenied) as e:
            detail = e.detail if isinstance(e.detail, str) else str(e.detail[0])
            return {"performed": False, "tag": tag_config.display, "message": detail}
        return {
            "performed": True,
            "tag": tag_config.display,
            "message": f"Tagged with \u201c{tag_config.display}\u201d",
        }

    @classmethod
    def authorize(cls, request, user, params: dict) -> bool:
        tag_id = params.get("tag")
        if not tag_id:
            raise ValidationError("A tag is required")
        tag_config = TagConfig.objects.filter(external_id=tag_id).first()
        if not tag_config:
            raise ValidationError("The chosen tag does not exist")
        if tag_config.resource != cls.resource.value:
            err = f"Tag \u201c{tag_config.display}\u201d is not a {cls.resource.value} tag"
            raise ValidationError(err)
        if not AuthorizationController.call("can_apply_tag_config", user, tag_config):
            err = f"You are not allowed to apply tag \u201c{tag_config.display}\u201d"
            raise ValidationError(err)
        return True


class TagEncounterInstruction(BaseTagInstruction):
    """Apply an encounter tag when the condition holds."""

    slug = "tag_encounter"
    context = EncounterContext
    input_schema = _tag_input(TagResource.encounter.value)
    resource = TagResource.encounter

    def resolve_target(self):
        return resolve_encounter(self.context)

    def tag_manager_for(self, tag_config, target):
        return SingleFacilityTagManager()

    def facility_for(self, tag_config, target):
        return target.facility


class TagPatientInstruction(BaseTagInstruction):
    """Apply a patient tag when the condition holds — a facility tag lands
    in that facility's tag set, an instance tag in the instance one."""

    slug = "tag_patient"
    context = PatientContext
    input_schema = _tag_input(TagResource.patient.value)
    resource = TagResource.patient

    def resolve_target(self):
        return resolve_patient(self.context)

    def tag_manager_for(self, tag_config, target):
        if tag_config.facility_id:
            return PatientFacilityTagManager(tag_config.facility)
        return PatientInstanceTagManager()


ActionInstructionRegistry.register(TagEncounterInstruction)
ActionInstructionRegistry.register(TagPatientInstruction)
