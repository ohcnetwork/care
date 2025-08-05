import uuid

from django.urls import reverse
from model_bakery import baker

from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
    ActivityDefinitionKindOptions,
    ActivityDefinitionStatusOptions,
)
from care.security.permissions.activity_definition import ActivityDefinitionPermissions
from care.utils.tests.base import CareAPITestBase


class ActivityDefinitionAPITestBase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="TestUser")
        self.superuser = self.create_super_user(username="SuperUser")
        self.facility = self.create_facility(name="Test Facility", user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            name="Test Facility Organization", facility=self.facility, org_type="root"
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                ActivityDefinitionPermissions.can_read_activity_definition.name,
                ActivityDefinitionPermissions.can_write_activity_definition.name,
            ]
        )
        self.base_url = self.get_base_url(facility=self.facility.external_id)
        self.facility_location = self.create_facility_location(
            facility=self.facility, name="Test Facility Location"
        )

    def generate_activity_definition_data(
        self, slug=None, title=None, status=None, category=None, kind=None, **kwargs
    ):
        return {
            "slug": slug or "test-activity-definition",
            "title": title or "Test Activity Definition",
            "derived_from_uri": None,
            "status": status or ActivityDefinitionStatusOptions.active.value,
            "description": "This is a test activity definition.",
            "usage": "Test usage",
            "category": category or ActivityDefinitionCategoryOptions.laboratory.value,
            "kind": kind or ActivityDefinitionKindOptions.service_request.value,
            "code": {"system": "http://example.com", "code": "12345"},
            "body_site": None,
            "diagnostic_report_codes": [],
            **kwargs,
        }

    def create_activity_definition(self, facility, **kwargs):
        data = self.generate_activity_definition_data(**kwargs)
        return baker.make(
            "emr.ActivityDefinition",
            **data,
            facility=facility,
            specimen_requirements=[self.generate_specimen_definition(facility).id],
            observation_result_requirements=[
                self.generate_observation_definition(facility).id
            ],
            healthcare_service=self.generate_healthcare_service(facility),
            charge_item_definitions=[self.charge_item_definition(facility).id],
        )

    def get_details_url(self, facility=None, activity_definition=None):
        return reverse(
            "activity_definition-detail",
            kwargs={
                "facility_external_id": facility,
                "external_id": activity_definition,
            },
        )

    def get_base_url(self, facility=None):
        return reverse(
            "activity_definition-list",
            kwargs={"facility_external_id": facility},
        )

    def generate_specimen_definition(self, facility):
        return baker.make(
            "emr.SpecimenDefinition",
            slug="test-specimen-definition",
            title="Test Specimen Definition",
            description="This is a test specimen definition.",
            facility=facility,
        )

    def generate_observation_definition(self, facility):
        return baker.make(
            "emr.ObservationDefinition",
            slug="test-observation-definition",
            title="Test Observation Definition",
            description="This is a test observation definition.",
            facility=facility,
        )

    def generate_healthcare_service(self, facility):
        return baker.make(
            "emr.HealthcareService", name="Test Healthcare Service", facility=facility
        )

    def charge_item_definition(self, facility):
        return baker.make(
            "emr.ChargeItemDefinition",
            slug="test-charge-item-definition",
            title="Test Charge Item Definition",
            description="This is a test charge item definition.",
            facility=facility,
        )

    def create_facility_location(self, facility, **kwargs):
        return baker.make("emr.FacilityLocation", facility=facility, **kwargs)

    # Test cases for create activity definition

    def test_create_activity_definition_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_activity_definition_as_user_with_permissions(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_activity_definition_as_user_without_permissions(self):
        self.client.force_authenticate(user=self.user)
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_activity_definition_with_invalid_facility(self):
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(
            self.get_base_url(facility="invalid-facility-id"), data, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_create_activity_definition_with_invalid_specimen(self):
        self.client.force_authenticate(user=self.superuser)
        invalid_specimen_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            specimen_requirements=[invalid_specimen_id],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Specimen Definition with id {invalid_specimen_id}",
            status_code=400,
        )

    def test_create_activity_definition_with_invalid_observation(self):
        self.client.force_authenticate(user=self.superuser)
        invalid_observation_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[invalid_observation_id],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Observation Definition with id {invalid_observation_id}",
            status_code=400,
        )

    def test_create_activity_definition_with_invalid_location(self):
        self.client.force_authenticate(user=self.superuser)
        invalid_location_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[invalid_location_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, f"Location with id {invalid_location_id}", status_code=400
        )

    def test_create_activity_definition_with_invalid_charge_item(self):
        self.client.force_authenticate(user=self.superuser)
        invalid_charge_item_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[invalid_charge_item_id],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Charge Item Definition with id {invalid_charge_item_id}",
            status_code=400,
        )

    def test_create_activity_definition_with_invalid_healthcare_service(self):
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_healthcare_service_id = self.generate_healthcare_service(
            another_facility
        ).external_id
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=invalid_healthcare_service_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Healthcare Service must be from the same facility",
            status_code=400,
        )

    def test_create_activity_definition_with_duplicate_slug(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_activity_definition(slug="duplicate-slug", facility=self.facility)
        data = self.generate_activity_definition_data(
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
            slug="duplicate-slug",
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Activity Definition with this slug already exists.",
            status_code=400,
        )

    # Test cases for update activity definition

    def test_update_activity_definition_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        facility_location2 = self.create_facility_location(facility=self.facility)
        activity_definition = self.create_activity_definition(facility=self.facility)
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[
                self.facility_location.external_id,
                facility_location2.external_id,
            ],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        get_response_data = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=response.data["id"],
            )
        ).data
        self.assertEqual(get_response_data["title"], "Updated Activity Definition")
        self.assertEqual(
            get_response_data["status"], ActivityDefinitionStatusOptions.retired.value
        )
        self.assertEqual(
            get_response_data["specimen_requirements"],
            response.data["specimen_requirements"],
        )
        self.assertEqual(
            get_response_data["observation_result_requirements"],
            response.data["observation_result_requirements"],
        )
        self.assertEqual(
            get_response_data["healthcare_service"], response.data["healthcare_service"]
        )
        self.assertEqual(
            get_response_data["charge_item_definitions"],
            response.data["charge_item_definitions"],
        )
        self.assertEqual(get_response_data["locations"], response.data["locations"])

    def test_update_activity_definition_as_user_with_permissions(self):
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)
        facility_location2 = self.create_facility_location(facility=self.facility)
        activity_definition = self.create_activity_definition(facility=self.facility)
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[
                self.facility_location.external_id,
                facility_location2.external_id,
            ],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        get_response_data = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=response.data["id"],
            )
        ).data
        self.assertEqual(get_response_data["title"], "Updated Activity Definition")
        self.assertEqual(
            get_response_data["status"], ActivityDefinitionStatusOptions.retired.value
        )
        self.assertEqual(
            get_response_data["specimen_requirements"],
            response.data["specimen_requirements"],
        )
        self.assertEqual(
            get_response_data["observation_result_requirements"],
            response.data["observation_result_requirements"],
        )
        self.assertEqual(
            get_response_data["healthcare_service"], response.data["healthcare_service"]
        )
        self.assertEqual(
            get_response_data["charge_item_definitions"],
            response.data["charge_item_definitions"],
        )
        self.assertEqual(get_response_data["locations"], response.data["locations"])

    def test_update_activity_definition_as_user_without_permissions(self):
        self.client.force_authenticate(user=self.user)
        activity_definition = self.create_activity_definition(facility=self.facility)
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_update_activity_definition_with_invalid_facility(self):
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(facility=self.facility)
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility="invalid-facility-id",
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_update_activity_definition_with_invalid_specimen(self):
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(facility=self.facility)
        invalid_specimen_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[invalid_specimen_id],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Specimen Definition with id {invalid_specimen_id}",
            status_code=400,
        )

    def test_update_activity_definition_with_invalid_observation(self):
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(facility=self.facility)
        invalid_observation_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[invalid_observation_id],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Observation Definition with id {invalid_observation_id}",
            status_code=400,
        )

    def test_update_activity_definition_with_invalid_location(self):
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(facility=self.facility)
        invalid_location_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[invalid_location_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, f"Location with id {invalid_location_id}", status_code=400
        )

    def test_update_activity_definition_with_invalid_charge_item(self):
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(facility=self.facility)
        invalid_charge_item_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[invalid_charge_item_id],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Charge Item Definition with id {invalid_charge_item_id}",
            status_code=400,
        )

    def test_update_activity_definition_with_invalid_healthcare_service(self):
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(facility=self.facility)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_healthcare_service_id = self.generate_healthcare_service(
            another_facility
        ).external_id
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=invalid_healthcare_service_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Healthcare Service must be from the same facility",
            status_code=400,
        )

    def test_update_activity_definition_with_healthcare_service_in_same_facility(self):
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(facility=self.facility)
        healthcare_service_id = self.generate_healthcare_service(
            self.facility
        ).external_id
        data = self.generate_activity_definition_data(
            slug=activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=healthcare_service_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=response.data["id"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["healthcare_service"]["id"], str(healthcare_service_id)
        )

    def test_update_activity_definition_with_duplicate_slug(self):
        self.client.force_authenticate(user=self.superuser)
        existing_activity_definition = self.create_activity_definition(
            slug="duplicate-slug", facility=self.facility
        )
        activity_definition = self.create_activity_definition(facility=self.facility)
        data = self.generate_activity_definition_data(
            slug=existing_activity_definition.slug,
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).external_id
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).external_id
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[
                self.charge_item_definition(self.facility).external_id
            ],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                activity_definition=activity_definition.external_id,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Activity Definition with this slug already exists.",
            status_code=400,
        )
