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


def setup_facility(ctx):
    """Create the primary facility, department org, locations, beds, and devices.

    Populates ctx.facility, ctx.facility_organization, ctx.location,
    and manifest entries for facility, locations, and devices.
    """
    from .organizations import create_facility_organization

    # Primary facility
    ctx.facility = create_facility(
        ctx.fake, ctx.super_user, ctx.geo_organization, "FACILITY WITH PATIENTS"
    )
    ctx.log(f"Created facility: {ctx.facility.name}")
    ctx.manifest["facility"] = {
        "id": str(ctx.facility.external_id),
        "name": ctx.facility.name,
    }

    # Facility organization (department)
    ctx.facility_organization = create_facility_organization(
        ctx.fake, ctx.super_user, ctx.facility
    )
    ctx.log(f"Created facility organization (dept): {ctx.facility_organization.name}")
    ctx.manifest["facility_organization_id"] = str(
        ctx.facility_organization.external_id
    )

    # Resource facility (second facility without patients)
    create_facility(ctx.fake, ctx.super_user, ctx.geo_organization)
    ctx.log("Created resource facility")

    # Primary ward location
    ctx.location = create_location(
        ctx.fake,
        ctx.super_user,
        ctx.facility,
        [ctx.facility_organization],
        mode="kind",
        form="wa",
    )
    ctx.log(f"Created location: {ctx.location.name}")

    # Beds
    manifest_locations = [
        {"id": str(ctx.location.external_id), "name": ctx.location.name}
    ]
    for i in range(1, 6):
        bed = create_location(
            ctx.fake,
            ctx.super_user,
            ctx.facility,
            [ctx.facility_organization],
            mode="instance",
            form="bd",
            parent=ctx.location.external_id,
            name=f"Bed {i}",
        )
        ctx.log(f"Created bed: {bed.name}")
        manifest_locations.append(
            {"id": str(bed.external_id), "name": bed.name}
        )
    ctx.manifest["locations"] = manifest_locations

    # Devices
    manifest_devices = []
    for i in range(1, 6):
        device = create_device(
            ctx.fake,
            ctx.super_user,
            ctx.facility_organization,
            name=f"Device {i}",
        )
        ctx.log(f"Created device: {device.user_friendly_name}")
        manifest_devices.append(
            {"id": str(device.external_id), "name": device.user_friendly_name}
        )
    ctx.manifest["devices"] = manifest_devices
