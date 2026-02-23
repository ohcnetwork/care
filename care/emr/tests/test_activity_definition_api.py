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
        self.resource_category = self.create_resource_category(
            facility=self.facility, slug="resource-category", title="Resource Category"
        )

    def generate_activity_definition_data(
        self,
        title=None,
        status=None,
        category=None,
        kind=None,
        classification=None,
        **kwargs,
    ):
        return {
            "title": title or "Test Activity Definition",
            "derived_from_uri": None,
            "status": status or ActivityDefinitionStatusOptions.active.value,
            "description": "This is a test activity definition.",
            "usage": "Test usage",
            "category": category or self.resource_category.slug,
            "classification": classification
            or ActivityDefinitionCategoryOptions.laboratory.value,
            "kind": kind or ActivityDefinitionKindOptions.service_request.value,
            "code": {"system": "http://example.com", "code": "12345"},
            "body_site": None,
            "diagnostic_report_codes": [],
            **kwargs,
        }

    def create_activity_definition(self, facility, slug, **kwargs):
        data = self.generate_activity_definition_data(**kwargs)
        return baker.make(
            "emr.ActivityDefinition",
            **data,
            facility=facility,
            slug=f"f-{facility.external_id}-{slug}",
            specimen_requirements=[self.generate_specimen_definition(facility).id],
            observation_result_requirements=[
                self.generate_observation_definition(facility).id
            ],
            healthcare_service=self.generate_healthcare_service(facility),
            charge_item_definitions=[self.charge_item_definition(facility).id],
        )

    def get_details_url(self, facility=None, slug=None):
        return reverse(
            "activity_definition-detail",
            kwargs={"facility_external_id": facility, "slug": slug},
        )

    def get_base_url(self, facility=None):
        return reverse(
            "activity_definition-list",
            kwargs={"facility_external_id": facility},
        )

    def generate_specimen_definition(self, facility):
        return baker.make(
            "emr.SpecimenDefinition",
            slug=f"f-{facility.external_id}-specimen-definition",
            title="Test Specimen Definition",
            description="This is a test specimen definition.",
            facility=facility,
        )

    def generate_observation_definition(self, facility):
        return baker.make(
            "emr.ObservationDefinition",
            slug=f"f-{facility.external_id}-observation-definition",
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
            slug=f"f-{facility.external_id}-charge-item-definition",
            title="Test Charge Item Definition",
            description="This is a test charge item definition.",
            facility=facility,
        )

    def create_facility_location(self, facility, **kwargs):
        return baker.make("emr.FacilityLocation", facility=facility, **kwargs)

    def create_resource_category(self, facility, slug=None, **kwargs):
        return baker.make(
            "emr.ResourceCategory",
            facility=facility,
            slug=f"f-{facility.external_id}-{slug or 'resource-category'}",
            resource_type="test-resource-type",
            **kwargs,
        )

    # Test cases for create activity definition

    def test_create_activity_definition_as_superuser(self):
        """Test creating an activity definition as a superuser"""

        self.client.force_authenticate(user=self.superuser)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_activity_definition_as_user_with_permissions(self):
        """Test creating an activity definition as a user with permissions"""
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_activity_definition_as_user_without_permissions(self):
        """Test creating an activity definition as a user without permissions"""
        self.client.force_authenticate(user=self.user)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_activity_definition_with_invalid_facility(self):
        """Test creating an activity definition with an invalid facility"""
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(
            self.get_base_url(facility="invalid-facility-id"), data, format="json"
        )
        self.assertEqual(response.status_code, 404)

    def test_create_activity_definition_with_invalid_specimen(self):
        """Test creating an activity definition with an invalid specimen"""
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_specimen = self.generate_specimen_definition(another_facility)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[invalid_specimen.slug],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Specimen Definition with slug {invalid_specimen.slug} not found",
            status_code=400,
        )

    def test_create_activity_definition_with_invalid_observation(self):
        """Test creating an activity definition with an invalid observation"""
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_observation = self.generate_observation_definition(another_facility)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[invalid_observation.slug],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Observation Definition with slug {invalid_observation.slug} not found",
            status_code=400,
        )

    def test_create_activity_definition_with_invalid_location(self):
        """Test creating an activity definition with an invalid location"""
        self.client.force_authenticate(user=self.superuser)
        invalid_location_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[invalid_location_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, f"Location with id {invalid_location_id}", status_code=400
        )

    def test_create_activity_definition_with_invalid_charge_item(self):
        """Test creating an activity definition with an invalid charge item"""
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_charge_item = self.charge_item_definition(another_facility)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[invalid_charge_item.slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Charge Item Definition with slug {invalid_charge_item.slug} not found",
            status_code=400,
        )

    def test_create_activity_definition_with_invalid_healthcare_service(self):
        """Test creating an activity definition with an invalid healthcare service"""
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_healthcare_service_id = self.generate_healthcare_service(
            another_facility
        ).external_id
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=invalid_healthcare_service_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
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
        """Test creating an activity definition with a duplicate slug in the same facility"""
        self.client.force_authenticate(user=self.superuser)
        self.create_activity_definition(
            slug="duplicate-slug",
            facility=self.facility,
            category=self.resource_category,
        )
        data = self.generate_activity_definition_data(
            slug_value="duplicate-slug",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Activity Definition with this slug already exists.",
            status_code=400,
        )

    def test_create_activity_definition_with_duplicate_slug_different_facility(self):
        """Test creating an activity definition with a duplicate slug in a different facility"""
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        self.create_activity_definition(
            slug="duplicate-slug",
            facility=another_facility,
            category=self.resource_category,
        )
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_activity_definition_without_category(self):
        """Test creating an activity definition without category"""
        self.client.force_authenticate(user=self.superuser)
        data = self.generate_activity_definition_data(
            slug_value="test-activity-definition",
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        data.pop("category")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Field required", response.data["errors"][0]["msg"])

    # Test cases for update activity definition

    def test_update_activity_definition_as_superuser(self):
        """Test updating an activity definition as a superuser"""
        self.client.force_authenticate(user=self.superuser)
        facility_location2 = self.create_facility_location(facility=self.facility)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[
                self.facility_location.external_id,
                facility_location2.external_id,
            ],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        get_response_data = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
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
        """Test updating an activity definition as a user with permissions"""
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)
        facility_location2 = self.create_facility_location(facility=self.facility)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[
                self.facility_location.external_id,
                facility_location2.external_id,
            ],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        get_response_data = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
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
        """Test updating an activity definition as a user without permissions"""
        self.client.force_authenticate(user=self.user)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_update_activity_definition_with_invalid_facility(self):
        """Test updating an activity definition with an invalid facility"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility="invalid-facility-id",
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response, "No Facility matches the given query.", status_code=404
        )

    def test_update_activity_definition_with_invalid_specimen(self):
        """Test updating an activity definition with an invalid specimen"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_specimen = self.generate_specimen_definition(another_facility)
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[invalid_specimen.slug],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Specimen Definition with slug {invalid_specimen.slug} not found",
            status_code=400,
        )

    def test_update_activity_definition_with_invalid_observation(self):
        """Test updating an activity definition with an invalid observation"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_observation = self.generate_observation_definition(another_facility)

        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[invalid_observation.slug],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Observation Definition with slug {invalid_observation.slug} not found",
            status_code=400,
        )

    def test_update_activity_definition_with_invalid_location(self):
        """Test updating an activity definition with an invalid location"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        invalid_location_id = uuid.uuid4()
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[invalid_location_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Location with id {invalid_location_id} not found",
            status_code=400,
        )

    def test_update_activity_definition_with_invalid_charge_item(self):
        """Test updating an activity definition with an invalid charge item"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_charge_item = self.charge_item_definition(another_facility)
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[invalid_charge_item.slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Charge Item Definition with slug {invalid_charge_item.slug} not found",
            status_code=400,
        )

    def test_update_activity_definition_with_invalid_healthcare_service(self):
        """Test updating an activity definition with an invalid healthcare service"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        invalid_healthcare_service_id = self.generate_healthcare_service(
            another_facility
        ).external_id
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=invalid_healthcare_service_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
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
        """Test updating an activity definition with a healthcare service in the same facility"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        healthcare_service_id = self.generate_healthcare_service(
            self.facility
        ).external_id
        data = self.generate_activity_definition_data(
            slug_value="updated-definition",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=healthcare_service_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(
            get_response.data["healthcare_service"]["id"], str(healthcare_service_id)
        )

    def test_update_activity_definition_with_duplicate_slug(self):
        """Test updating an activity definition with a duplicate slug in the same facility"""
        self.client.force_authenticate(user=self.superuser)
        self.create_activity_definition(
            slug="duplicate-slug",
            facility=self.facility,
            category=self.resource_category,
        )
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        data = self.generate_activity_definition_data(
            slug_value="duplicate-slug",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
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

    def test_update_activity_definition_with_duplicate_slug_different_facility(self):
        """Test updating an activity definition with a duplicate slug in a different facility"""
        self.client.force_authenticate(user=self.superuser)
        another_facility = self.create_facility(
            name="Another Facility", user=self.superuser
        )
        self.create_activity_definition(
            slug="duplicate-slug",
            facility=another_facility,
            category=self.resource_category,
        )
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            category=self.resource_category,
            slug="Test-Activity-Definition",
        )
        data = self.generate_activity_definition_data(
            slug_value="duplicate-slug",
            title="Updated Activity Definition",
            status=ActivityDefinitionStatusOptions.retired.value,
            specimen_requirements=[
                self.generate_specimen_definition(self.facility).slug
            ],
            observation_result_requirements=[
                self.generate_observation_definition(self.facility).slug
            ],
            healthcare_service=self.generate_healthcare_service(
                self.facility
            ).external_id,
            charge_item_definitions=[self.charge_item_definition(self.facility).slug],
            locations=[self.facility_location.external_id],
        )
        response = self.client.put(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=activity_definition.slug,
            ),
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_details_url(
                facility=self.facility.external_id,
                slug=response.data["slug"],
            )
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    # Test cases for list activity definitions

    def test_list_activity_definitions_as_superuser(self):
        """Test listing activity definitions as a superuser"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition1 = self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition",
            category=self.resource_category,
        )
        activity_definition2 = self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition-2",
            category=self.resource_category,
        )
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][1]["slug"], str(activity_definition1.slug)
        )
        self.assertEqual(
            response.data["results"][0]["slug"], str(activity_definition2.slug)
        )

    def test_list_activity_definitions_as_user_with_permissions(self):
        """Test listing activity definitions as a user with permissions"""
        self.attach_role_facility_organization_user(
            user=self.user,
            facility_organization=self.facility_organization,
            role=self.role,
        )
        self.client.force_authenticate(user=self.user)
        activity_definition1 = self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition",
            category=self.resource_category,
        )
        activity_definition2 = self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition-2",
            category=self.resource_category,
        )
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][1]["slug"], str(activity_definition1.slug)
        )
        self.assertEqual(
            response.data["results"][0]["slug"], str(activity_definition2.slug)
        )

    def test_list_activity_definitions_as_user_without_permissions(self):
        """Test listing activity definitions as a user without permissions"""
        self.client.force_authenticate(user=self.user)
        self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition",
            category=self.resource_category,
        )
        self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition-2",
            category=self.resource_category,
        )
        response = self.client.get(self.base_url, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Access Denied to Activity Definition",
            status_code=403,
        )

    def test_list_activity_definition_with_status_filter(self):
        """Test listing activity definitions with status filter"""
        self.client.force_authenticate(user=self.superuser)
        activity_definition1 = self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition",
            status=ActivityDefinitionStatusOptions.active.value,
            category=self.resource_category,
        )
        self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition-2",
            status=ActivityDefinitionStatusOptions.retired.value,
            category=self.resource_category,
        )
        response = self.client.get(
            self.base_url,
            {"status": ActivityDefinitionStatusOptions.active.value},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["slug"], str(activity_definition1.slug)
        )
        self.assertEqual(
            response.data["results"][0]["status"],
            ActivityDefinitionStatusOptions.active.value,
        )

    def test_list_activity_definition_with_category_filter(self):
        """Test filtering activity definitions by dummy category filter."""

        self.client.force_authenticate(user=self.superuser)

        activity_definition_1 = self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition",
            category=self.resource_category,
        )
        activity_definition_2 = self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition-2",
            category=self.resource_category,
        )
        response = self.client.get(
            self.base_url, {"category": self.resource_category.slug}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(
            response.data["results"][0]["slug"], str(activity_definition_2.slug)
        )
        self.assertEqual(
            response.data["results"][1]["slug"], str(activity_definition_1.slug)
        )
        self.assertEqual(
            response.data["results"][0]["category"]["id"],
            str(self.resource_category.external_id),
        )

    def test_list_activity_definition_with_kind_filter(self):
        """Test listing activity definitions with kind filter"""
        self.client.force_authenticate(user=self.superuser)
        self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition",
            kind="Test Kind",
            category=self.resource_category,
        )
        self.create_activity_definition(
            facility=self.facility,
            slug="test-activity-definition-2",
            kind="Another Kind",
            category=self.resource_category,
        )
        response = self.client.get(self.base_url, {"kind": "Test Kind"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["slug"],
            f"f-{self.facility.external_id}-test-activity-definition",
        )
        self.assertEqual(response.data["results"][0]["kind"], "Test Kind")

    def test_list_activity_definition_with_invalid_facility(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_base_url(facility="invalid-facility-id"), format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response,
            "No Facility matches the given query.",
            status_code=404,
        )

    def test_list_activity_definition_with_include_children_with_is_child_false(self):
        """
        Test to list activity definitions with dummy filter include_children set to false to view only the activity definitions in the parent category.
        """
        self.client.force_authenticate(user=self.superuser)
        activity_definition = self.create_activity_definition(
            facility=self.facility,
            slug="parent-activity",
            category=self.resource_category,
        )
        child_resource_category = self.create_resource_category(
            facility=self.facility,
            slug="child-category",
            parent=self.resource_category,
            is_child=True,
        )
        self.create_activity_definition(
            facility=self.facility,
            slug="sub-activity-definition",
            category=child_resource_category,
            title="Sub Category Activity Definition",
        )
        response = self.client.get(
            self.base_url,
            {"include_children": "false", "category": self.resource_category.slug},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(activity_definition.external_id)
        )

    def test_list_activity_definition_with_include_children_with_is_child_true(self):
        """
        Test to list activity definitions with dummy filter include_children set to true to view only the activity definitions in child categories.
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_activity_definition(
            facility=self.facility,
            slug="parent-activity",
            category=self.resource_category,
        )
        child_resource_category = self.create_resource_category(
            facility=self.facility,
            slug="child-category",
            parent=self.resource_category,
            is_child=True,
        )
        child_activity_definition = self.create_activity_definition(
            facility=self.facility,
            slug="sub-activity-definition",
            category=child_resource_category,
            title="Sub Category Activity Definition",
        )
        response = self.client.get(
            self.base_url,
            {"include_children": "true", "category": self.resource_category.slug},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"],
            str(child_activity_definition.external_id),
        )
