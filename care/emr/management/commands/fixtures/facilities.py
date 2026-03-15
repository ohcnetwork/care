from care.emr.models import FacilityLocationOrganization
from care.emr.resources.device.spec import DeviceCreateSpec
from care.emr.resources.facility.spec import FacilityCreateSpec
from care.emr.resources.location.spec import FacilityLocationWriteSpec

from . import generate_unique_indian_phone_number


def create_facility(fake, super_user, geo_organization, name=None):
    facility_spec = FacilityCreateSpec(
        geo_organization=geo_organization.external_id,
        name=name or fake.company(),
        description=fake.text(max_nb_chars=200),
        longitude=float(fake.longitude()),
        latitude=float(fake.latitude()),
        pincode=fake.random_int(min=100000, max=999999),
        address=fake.address(),
        phone_number=generate_unique_indian_phone_number(),
        middleware_address=fake.address(),
        facility_type="Private Hospital",
        is_public=True,
        features=[1],
    )
    facility = facility_spec.de_serialize()
    facility.created_by = super_user
    facility.updated_by = super_user
    facility.save()
    return facility


def create_location(
    fake,
    super_user,
    facility,
    organizations,
    mode,
    form,
    parent=None,
    name=None,
):
    location_spec = FacilityLocationWriteSpec(
        organizations=[],
        parent=parent,
        status="active",
        operational_status="O",
        name=name or fake.company(),
        description=fake.text(max_nb_chars=200),
        mode=mode,
        form=form,
    )
    location = location_spec.de_serialize()
    location.facility = facility
    location.created_by = super_user
    location.updated_by = super_user
    location.save()

    for organization in organizations:
        FacilityLocationOrganization.objects.create(
            location=location, organization=organization
        )
    return location


def create_device(fake, super_user, facility_organization, name=None):
    name = name or fake.company()
    device_spec = DeviceCreateSpec(
        registered_name=name,
        user_friendly_name=name,
        status="active",
        availability_status="available",
        manufacturer=fake.company(),
    )
    device = device_spec.de_serialize()
    device.facility = facility_organization.facility
    device.managing_organization = facility_organization
    device.created_by = super_user
    device.updated_by = super_user
    device.save()
    return device
