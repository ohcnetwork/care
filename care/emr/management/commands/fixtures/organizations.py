from care.emr.models import Organization
from care.emr.models.organization import FacilityOrganizationUser, OrganizationUser
from care.emr.resources.facility_organization.spec import (
    FacilityOrganizationTypeChoices,
    FacilityOrganizationWriteSpec,
)
from care.emr.resources.organization.spec import (
    OrganizationTypeChoices,
    OrganizationWriteSpec,
)

from . import ROLES_OPTIONS


def create_organization(fake, super_user, **kwargs):
    data = {
        "active": True,
        "org_type": OrganizationTypeChoices.govt,
        "name": fake.state(),
    }
    if kwargs:
        data.update(kwargs)

    org_spec = OrganizationWriteSpec(**data)
    org = org_spec.de_serialize()
    org.created_by = super_user
    org.updated_by = super_user
    org.save()
    return org


def create_role_organizations(fake, super_user):
    orgs = []
    for role_name in ROLES_OPTIONS:
        if Organization.objects.filter(
            name=role_name, org_type=OrganizationTypeChoices.role
        ).exists():
            continue
        org_spec = OrganizationWriteSpec(
            active=True, org_type=OrganizationTypeChoices.role, name=role_name
        )
        org = org_spec.de_serialize()
        org.created_by = super_user
        org.updated_by = super_user
        org.save()
        orgs.append(org)
    return orgs


def create_facility_organization(fake, super_user, facility):
    org_spec = FacilityOrganizationWriteSpec(
        active=True,
        name=fake.company(),
        description=fake.text(max_nb_chars=200),
        facility=facility.external_id,
        org_type=FacilityOrganizationTypeChoices.dept,
    )
    org = org_spec.de_serialize()
    org.created_by = super_user
    org.updated_by = super_user
    org.save()
    return org


def attach_role_organization_user(organization, user, role):
    return OrganizationUser.objects.create(
        organization=organization, user=user, role=role
    )


def attach_role_facility_organization_user(facility_organization, user, role):
    return FacilityOrganizationUser.objects.create(
        organization=facility_organization, user=user, role=role
    )
