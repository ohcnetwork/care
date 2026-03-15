import json
from pathlib import Path

from care.emr.models import (
    FacilityOrganization,
    Organization,
    Questionnaire,
    QuestionnaireOrganization,
)
from care.emr.resources.organization.spec import OrganizationTypeChoices
from care.emr.resources.questionnaire.spec import QuestionnaireSpec

from . import ROLES_OPTIONS


def setup_questionnaires(ctx):
    """Create questionnaires for the primary facility."""
    create_questionnaires(ctx.facility, ctx.super_user)
    ctx.log("Created questionnaires")


def create_questionnaires(facility, super_user):
    with Path.open("data/questionnaire_fixtures.json") as f:
        questionnaires = json.load(f)

    roles = Organization.objects.filter(
        name__in=ROLES_OPTIONS.keys(), org_type=OrganizationTypeChoices.role
    )

    facility_organizations = FacilityOrganization.objects.filter(
        facility=facility,
    ).values_list("external_id", flat=True)

    for questionnaire in questionnaires:
        questionnaire_slug = questionnaire["slug"]
        if Questionnaire.objects.filter(slug=questionnaire_slug).exists():
            continue

        questionnaire["organizations"] = facility_organizations
        questionnaire["tags"] = []

        questionnaire_spec = QuestionnaireSpec(**questionnaire)

        questionnaire_spec = questionnaire_spec.de_serialize()

        questionnaire_spec.created_by = super_user
        questionnaire_spec.updated_by = super_user
        questionnaire_spec.save()

        for role in roles:
            QuestionnaireOrganization.objects.create(
                questionnaire=questionnaire_spec,
                organization=role,
            )
