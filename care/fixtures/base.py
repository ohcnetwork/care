import json
import re
import secrets
import string
from collections import UserDict
from pathlib import Path
from secrets import choice

from django.urls import reverse
from faker import Faker
from rest_framework import status as http_status

from care.emr.resources.device.spec import (
    DeviceAvailabilityStatusChoices,
    DeviceStatusChoices,
)
from care.emr.resources.encounter.constants import (
    ClassChoices,
    EncounterPriorityChoices,
)
from care.emr.resources.encounter.constants import (
    StatusChoices as EncounterStatusChoices,
)
from care.emr.resources.location.spec import (
    FacilityLocationFormChoices,
    FacilityLocationModeChoices,
    FacilityLocationOperationalStatusChoices,
)
from care.emr.resources.location.spec import StatusChoices as LocationStatusChoices
from care.emr.resources.patient.spec import BloodGroupChoices, GenderChoices
from care.facility.models.facility import REVERSE_FACILITY_TYPES, FacilityFeature


class FixtureError(Exception):
    pass


class AttributeDict(UserDict):
    """Allows attribute access (obj.id for a dict api response)."""

    def __getattr__(self, key):
        try:
            return self.data[key]
        except KeyError:
            raise AttributeError(key) from None

    def __setattr__(self, key, value):
        if (
            key == "data"
        ):  # this is to avoid overwriting the inner data dict of UserDict
            super().__setattr__(key, value)
        else:
            self.data[key] = value


def to_attr_dict(obj):
    if isinstance(obj, dict):
        return AttributeDict({k: to_attr_dict(v) for k, v in obj.items()})
    if isinstance(obj, list):
        return [to_attr_dict(item) for item in obj]
    return obj


def generate_phone_number():
    prefix = secrets.choice(["6", "7", "8", "9"])
    suffix = "".join(secrets.choice(string.digits) for _ in range(9))
    return f"+91{prefix}{suffix}"


def slugify(text, max_length=36):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_length]
    return slug if len(slug) >= 5 else slug.ljust(5, "-")  # noqa: PLR2004


class CareFixtureBase:
    """
    Simple class with helper functions to create fixtures.
    Inspired by CareAPITestBase (We should merge these in future)
    """

    fake = Faker("en_IN")

    def __init__(self, client):
        self.client = client

    def post(self, url, data):
        response = self.client.post(url, data, format="json")
        if response.status_code not in (
            http_status.HTTP_200_OK,
            http_status.HTTP_201_CREATED,
        ):
            msg = f"POST {url} failed ({response.status_code}): {response.data}"
            raise FixtureError(msg)
        return to_attr_dict(response.data)

    def patch(self, url, data):
        response = self.client.patch(url, data, format="json")
        if response.status_code not in (
            http_status.HTTP_200_OK,
            http_status.HTTP_201_CREATED,
        ):
            msg = f"PATCH {url} failed ({response.status_code}): {response.data}"
            raise FixtureError(msg)
        return to_attr_dict(response.data)

    def get(self, url, params=None):
        response = self.client.get(url, params or {}, format="json")
        if response.status_code != http_status.HTTP_200_OK:
            msg = f"GET {url} failed ({response.status_code}): {response.data}"
            raise FixtureError(msg)
        return to_attr_dict(response.data)

    def create_organization(self, org_type="govt", **kwargs):
        data = {
            "name": self.fake.state() if org_type == "govt" else self.fake.company(),
            "org_type": org_type,
            "active": True,
            **kwargs,
        }
        return self.post(reverse("organization-list"), data)

    def create_facility(self, geo_organization, **kwargs):
        data = {
            "name": self.fake.company() + " Hospital",
            "description": self.fake.paragraph(),
            "facility_type": choice(list(REVERSE_FACILITY_TYPES.values())),
            "address": self.fake.address(),
            "pincode": self.fake.random_int(min=100000, max=999999),
            "phone_number": generate_phone_number(),
            "latitude": float(self.fake.latitude()),
            "longitude": float(self.fake.longitude()),
            "is_public": self.fake.boolean(),
            "geo_organization": geo_organization,
            "features": [choice([f.value for f in FacilityFeature])],
            **kwargs,
        }
        return self.post(reverse("facility-list"), data)

    def get_facility_organizations(self, facility_id):
        url = reverse(
            "facility-organization-list",
            kwargs={"facility_external_id": facility_id},
        )
        data = self.get(url)
        return data.get("results", [])

    def create_facility_organization(self, facility_id, **kwargs):
        url = reverse(
            "facility-organization-list",
            kwargs={"facility_external_id": facility_id},
        )
        data = {
            "name": self.fake.bs().title(),
            "org_type": "team",
            "active": True,
            "description": self.fake.sentence(),
            **kwargs,
        }
        return self.post(url, data)

    def add_user_to_facility_organization(
        self, facility_id, facility_organization_id, user_id, role_id
    ):
        url = reverse(
            "facility-organization-users-list",
            kwargs={
                "facility_external_id": facility_id,
                "facility_organizations_external_id": facility_organization_id,
            },
        )
        return self.post(url, {"user": user_id, "role": role_id})

    def create_location(self, facility_id, **kwargs):
        url = reverse("location-list", kwargs={"facility_external_id": facility_id})
        data = {
            "name": f"Location {self.fake.random_uppercase_letter()}",
            "description": self.fake.sentence(),
            "form": FacilityLocationFormChoices.bd.value,
            "status": LocationStatusChoices.active.value,
            "operational_status": FacilityLocationOperationalStatusChoices.O.value,
            "mode": FacilityLocationModeChoices.instance.value,
            **kwargs,
        }
        return self.post(url, data)

    def add_organization_to_location(self, facility_id, location_id, organization_id):
        url = reverse(
            "location-organizations-add",
            kwargs={
                "facility_external_id": facility_id,
                "external_id": location_id,
            },
        )
        return self.post(url, {"organization": organization_id})

    def create_device(self, facility_id, **kwargs):
        url = reverse("device-list", kwargs={"facility_external_id": facility_id})
        data = {
            "registered_name": self.fake.word().title() + " Device",
            "status": DeviceStatusChoices.active.value,
            "availability_status": DeviceAvailabilityStatusChoices.available.value,
            "identifier": f"DEV-{self.fake.unique.random_int(min=1000, max=9999)}",
            **kwargs,
        }
        return self.post(url, data)

    def get_roles(self):
        data = self.get(reverse("role-list"))
        results = data.get("results", data)
        return {role.name: role for role in results}

    def create_user(self, geo_organization, role_orgs=None, **kwargs):
        data = {
            "username": self.fake.user_name(),
            "first_name": self.fake.first_name(),
            "last_name": self.fake.last_name(),
            "email": self.fake.email(),
            "password": "Ohcn@123",
            "phone_number": generate_phone_number(),
            "gender": GenderChoices.male.value,
            "geo_organization": geo_organization,
            "role_orgs": role_orgs or [],
            **kwargs,
        }
        return self.post(reverse("users-list"), data)

    def create_patient(self, geo_organization, **kwargs):
        data = {
            "name": self.fake.name(),
            "gender": choice([g.value for g in GenderChoices]),
            "phone_number": generate_phone_number(),
            "geo_organization": geo_organization,
            "address": self.fake.address(),
            "pincode": self.fake.random_int(min=100000, max=999999),
            "date_of_birth": self.fake.date_of_birth(
                minimum_age=18, maximum_age=80
            ).isoformat(),
            "blood_group": choice(
                [b.value for b in BloodGroupChoices if b.value != "unknown"]
            ),
            **kwargs,
        }
        return self.post(reverse("patient-list"), data)

    def create_encounter(self, patient_id, facility_id, organizations=None, **kwargs):
        data = {
            "patient": patient_id,
            "facility": facility_id,
            "status": choice(
                [s.value for s in EncounterStatusChoices if s.value != "unknown"]
            ),
            "encounter_class": choice([c.value for c in ClassChoices]),
            "priority": choice([p.value for p in EncounterPriorityChoices]),
            "organizations": organizations or [],
            **kwargs,
        }
        return self.post(reverse("encounter-list"), data)

    def create_questionnaire(self, organizations, data):
        questionnaire_data = {**data, "organizations": organizations}
        return self.post(reverse("questionnaire-list"), questionnaire_data)

    def load_questionnaires_from_file(
        self, organizations, path="data/questionnaire_fixtures.json"
    ):
        fixture_path = Path(path)
        if not fixture_path.exists():
            return []
        with fixture_path.open() as f:
            questionnaires = json.load(f)
        results = []
        for questionnaire_data in questionnaires:
            try:
                result = self.create_questionnaire(organizations, questionnaire_data)
                results.append(result)
            except FixtureError:
                pass
        return results

    def create_resource_category(self, facility_id, title, resource_type, **kwargs):
        url = reverse(
            "resource_category-list",
            kwargs={"facility_external_id": facility_id},
        )
        data = {
            "title": title,
            "resource_type": resource_type,
            "resource_sub_type": "other",
            "slug_value": slugify(f"{title}-{resource_type}"),
            **kwargs,
        }
        return self.post(url, data)

    def create_specimen_definition(self, facility_id, title, **kwargs):
        url = reverse(
            "specimen_definition-list",
            kwargs={"facility_external_id": facility_id},
        )
        data = {
            "title": title,
            "status": "active",
            "description": "",
            "type_collected": {},
            "slug_value": slugify(title),
            **kwargs,
        }
        return self.post(url, data)

    def create_observation_definition(
        self,
        title,
        code,
        category,
        permitted_data_type,
        qualified_ranges,
        facility=None,
        **kwargs,
    ):
        data = {
            "title": title,
            "status": "active",
            "description": "",
            "category": category,
            "code": code,
            "permitted_data_type": permitted_data_type,
            "qualified_ranges": qualified_ranges,
            "slug_value": slugify(title),
            **kwargs,
        }
        if facility:
            data["facility"] = facility
        return self.post(reverse("observation_definition-list"), data)

    def create_healthcare_service(self, facility_id, name, **kwargs):
        url = reverse(
            "healthcare_service-list",
            kwargs={"facility_external_id": facility_id},
        )
        data = {
            "name": name,
            "managing_organization": None,
            **kwargs,
        }
        return self.post(url, data)

    def create_charge_item_definition(
        self, facility_id, title, price_components, **kwargs
    ):
        url = reverse(
            "charge_item_definition-list",
            kwargs={"facility_external_id": facility_id},
        )
        data = {
            "status": "active",
            "title": title,
            "slug_value": slugify(title),
            "price_components": price_components,
            "can_edit_charge_item": True,
            "discount_configuration": None,
            **kwargs,
        }
        return self.post(url, data)

    def create_activity_definition(
        self,
        facility_id,
        title,
        code,
        locations,
        specimen_requirements,
        observation_result_requirements,
        charge_item_definitions,
        **kwargs,
    ):
        url = reverse(
            "activity_definition-list",
            kwargs={"facility_external_id": facility_id},
        )
        data = {
            "title": title,
            "status": "active",
            "classification": "laboratory",
            "kind": "service_request",
            "code": code,
            "slug_value": slugify(title),
            "locations": locations,
            "specimen_requirements": specimen_requirements,
            "observation_result_requirements": observation_result_requirements,
            "charge_item_definitions": charge_item_definitions,
            "healthcare_service": None,
            **kwargs,
        }
        return self.post(url, data)

    def create_product_knowledge(self, name, base_unit, facility=None, **kwargs):
        data = {
            "status": "active",
            "product_type": "medication",
            "name": name,
            "base_unit": base_unit,
            "slug_value": slugify(name),
            **kwargs,
        }
        if facility:
            data["facility"] = facility
        return self.post(reverse("product_knowledge-list"), data)

    def create_product(self, facility_id, product_knowledge_slug, **kwargs):
        url = reverse("product-list", kwargs={"facility_external_id": facility_id})
        data = {
            "status": "active",
            "product_knowledge": product_knowledge_slug,
            "extensions": {},
            **kwargs,
        }
        return self.post(url, data)

    def create_request_order(self, facility_id, name, destination, **kwargs):
        url = reverse(
            "request-order-list", kwargs={"facility_external_id": facility_id}
        )
        data = {
            "status": "pending",
            "name": name,
            "destination": destination,
            "intent": "order",
            "category": "central",
            "priority": "routine",
            "reason": "ward_stock",
            **kwargs,
        }
        return self.post(url, data)

    def create_supply_request(self, order, item, quantity, **kwargs):
        data = {
            "status": "active",
            "order": order,
            "item": item,
            "quantity": quantity,
            **kwargs,
        }
        return self.post(reverse("supply_request-list"), data)

    def create_delivery_order(self, facility_id, name, destination, **kwargs):
        url = reverse(
            "delivery-order-list", kwargs={"facility_external_id": facility_id}
        )
        data = {
            "status": "pending",
            "name": name,
            "destination": destination,
            "extensions": {},
            **kwargs,
        }
        return self.post(url, data)

    def create_supply_delivery(self, order, supplied_item_quantity, **kwargs):
        data = {
            "status": "in_progress",
            "order": order,
            "supplied_item_quantity": supplied_item_quantity,
            "extensions": {},
            **kwargs,
        }
        return self.post(reverse("supply_delivery-list"), data)

    def update_supply_delivery(self, delivery_id, **kwargs):
        url = reverse("supply_delivery-detail", kwargs={"external_id": delivery_id})
        return self.patch(url, kwargs)

    def list_inventory_items(self, facility_id, location_id, **params):
        url = reverse(
            "inventory-item-list",
            kwargs={
                "facility_external_id": facility_id,
                "location_external_id": location_id,
            },
        )
        return self.get(url, params=params).get("results", [])

    def create_lab_test(
        self,
        facility_id,
        test,
        service_id,
        location_id,
        charge_category_slug,
        activity_category_slug,
    ):
        """Create a complete lab test: specimen -> observation -> charge_item_definition -> activity_definition."""

        specimen = self.create_specimen_definition(facility_id, **test["specimen"])
        observation = self.create_observation_definition(
            facility=facility_id, **test["observation"]
        )
        charge_item_definition = self.create_charge_item_definition(
            facility_id,
            category=charge_category_slug,
            **test["charge_item_definition"],
        )

        activity_config = {**test["activity"]}
        self.create_activity_definition(
            facility_id,
            locations=[location_id],
            specimen_requirements=[specimen.slug],
            observation_result_requirements=[observation.slug],
            charge_item_definitions=[charge_item_definition.slug],
            healthcare_service=service_id,
            category=activity_category_slug,
            **activity_config,
        )

    def create_facility_product(self, facility_id, item, category_slugs):
        """Create a Product (with its ProductKnowledge + ChargeItemDefinition)."""

        product_knowledge = self.create_product_knowledge(
            category=category_slugs["product_knowledge"], **item["product_knowledge"]
        )
        charge_item_definition = self.create_charge_item_definition(
            facility_id,
            category=category_slugs["charge_item_definition"],
            **item["charge_item_definition"],
        )
        product = self.create_product(
            facility_id,
            product_knowledge_slug=product_knowledge.slug,
            charge_item_definition=charge_item_definition.slug,
            **item.get("product_extras", {}),
        )
        return product, product_knowledge

    def link_managing_org(self, role_org_id, managing_org_id):
        url = reverse(
            "organization-managing-organization",
            kwargs={"external_id": role_org_id},
        )
        return self.post(url, {"organization": managing_org_id, "action": "add"})

    def assign_org_role(self, org_id, user_id, role_id):
        url = reverse(
            "organization-users-list",
            kwargs={"organization_external_id": org_id},
        )
        return self.post(url, {"user": user_id, "role": role_id})

    def get_role_org_roles(self):
        data = self.get(reverse("role-list"), params={"context": "ROLE_ORG"})
        results = data.get("results", data)
        return {r.name: r for r in results}

    def get_user(self, username):
        return self.get(reverse("users-detail", kwargs={"username": username}))

    def create_schedule(self, facility_id, resource_type, resource_id, **kwargs):
        url = reverse("schedule-list", kwargs={"facility_external_id": facility_id})
        data = {
            "facility": facility_id,
            "name": "Default Schedule",
            "resource_type": resource_type,
            "resource_id": resource_id,
            "is_public": True,
            "availabilities": [],
            **kwargs,
        }
        return self.post(url, data)

    def get_slots_for_day(self, facility_id, resource_type, resource_id, day):
        url = reverse(
            "slot-get-slots-for-day",
            kwargs={"facility_external_id": facility_id},
        )
        data = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "day": day,
        }
        return self.post(url, data)

    def create_appointment(self, facility_id, slot_id, patient_id, note=""):
        url = reverse(
            "slot-create-appointment",
            kwargs={
                "facility_external_id": facility_id,
                "external_id": slot_id,
            },
        )
        return self.post(url, {"patient": patient_id, "note": note})

    def create_token_queue(self, facility_id, resource_type, resource_id, **kwargs):
        url = reverse("token-queue-list", kwargs={"facility_external_id": facility_id})
        data = {
            "name": "Default Queue",
            "resource_type": resource_type,
            "resource_id": resource_id,
            **kwargs,
        }
        return self.post(url, data)

    def create_token_sub_queue(self, facility_id, resource_type, resource_id, **kwargs):
        url = reverse(
            "token-sub-queue-list", kwargs={"facility_external_id": facility_id}
        )
        data = {
            "name": "Default Service Point",
            "status": "active",
            "resource_type": resource_type,
            "resource_id": resource_id,
            **kwargs,
        }
        return self.post(url, data)

    def create_token_category(self, facility_id, resource_type, **kwargs):
        url = reverse(
            "token-category-list", kwargs={"facility_external_id": facility_id}
        )
        data = {
            "name": f"{resource_type.capitalize()} Token Category",
            "resource_type": resource_type,
            "shorthand": resource_type[:5].upper(),
            **kwargs,
        }
        return self.post(url, data)

    def create_template(
        self,
        name,
        slug_value,
        template_data,
        template_type="discharge_summary",
        context="encounter_base",
        facility=None,
        **kwargs,
    ):
        url = reverse("template-list")
        data = {
            "name": name,
            "slug_value": slug_value,
            "template_data": template_data,
            "template_type": template_type,
            "context": context,
            "status": "active",
            "default_format": "html",
            "facility": facility,
            **kwargs,
        }
        return self.post(url, data)

    def load_templates_from_file(
        self, facility=None, path="data/template_fixtures.json"
    ):
        fixture_path = Path(path)
        if not fixture_path.exists():
            return []
        with fixture_path.open() as f:
            templates = json.load(f)
        results = []
        for entry in templates:
            try:
                results.append(self.create_template(facility=facility, **entry))
            except FixtureError:
                pass
        return results
