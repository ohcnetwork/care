from secrets import choice

from django.urls import reverse
from model_bakery import baker

from care.emr.resources.observation_definition.spec import (
    ObservationCategoryChoices,
    ObservationStatusChoices,
)
from care.emr.resources.questionnaire.spec import QuestionType
from care.security.permissions.observation_definition import (
    ObservationDefinitionPermissions,
)
from care.utils.tests.base import CareAPITestBase


class ObservationDefinitionAPITest(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="testuser")
        self.superuser = self.create_super_user(username="superuser")
        self.facility = self.create_facility(user=self.superuser)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility, org_type="root"
        )

        self.role = self.create_role_with_permissions(
            permissions=[
                ObservationDefinitionPermissions.can_write_observation_definition.name,
                ObservationDefinitionPermissions.can_read_observation_definition.name,
            ],
        )
        self.observation_definition_data = {
            "title": "Blood Pressure",
            "slug": "blood-pressure",
            "category": ObservationCategoryChoices.vital_signs.value,
            "status": ObservationStatusChoices.active.value,
            "description": "Definition for measuring blood pressure",
            "code": {
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children",
            },
            "facility": self.facility.external_id,
            "permitted_data_type": QuestionType.quantity.value,
        }
        self.url = reverse("observation_definition-list")

    def get_detail_url(self, external_id):
        return reverse(
            "observation_definition-detail",
            kwargs={
                "external_id": external_id,
            },
        )

    def create_observation_definition(self, **kwargs):
        return baker.make(
            "ObservationDefinition",
            category=self.observation_definition_data["category"],
            description=self.observation_definition_data["description"],
            code=self.observation_definition_data["code"],
            permitted_data_type=self.observation_definition_data["permitted_data_type"],
            status=self.observation_definition_data["status"],
            **kwargs,
        )

    def test_create_observation_definition_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url, self.observation_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_observation_definition_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url, self.observation_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_observation_definition_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url, self.observation_definition_data, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_create_observation_definition_as_superuser_without_facility(self):
        self.client.force_authenticate(user=self.superuser)
        invalid_data = self.observation_definition_data.copy()
        invalid_data.pop("facility")
        response = self.client.post(self.url, invalid_data, format="json")
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["id"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_observation_definition_as_user_without_facility(self):
        self.client.force_authenticate(user=self.user)
        invalid_data = self.observation_definition_data.copy()
        invalid_data.pop("facility")
        response = self.client.post(self.url, invalid_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "Access Denied to Observation Definition",
            status_code=403,
        )

    def test_create_observation_definition_with_duplicate_slug(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_observation_definition(
            facility=self.facility,
            slug="blood-pressure",
        )
        response = self.client.post(
            self.url,
            self.observation_definition_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Slug must be unique",
            str(response.data),
        )

    def test_create_observation_definiton_with_invalid_permitted_data_type(self):
        self.client.force_authenticate(user=self.superuser)
        invalid_question_types = ["group", "display", "url"]
        invalid_data = self.observation_definition_data.copy()
        invalid_data["permitted_data_type"] = choice(invalid_question_types)
        response = self.client.post(self.url, invalid_data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "permitted_data_type",
            str(response.data),
        )
        self.assertIn("Cannot create a definition with this type", str(response.data))

    # Test cases for retrieve observation definition

    def test_retrieve_observation_definition_as_superuser(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url(observation_definition.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(observation_definition.external_id))

    def test_retrieve_observation_definition_as_user_with_permission(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(observation_definition.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(observation_definition.external_id))

    def test_retrieve_observation_definition_without_permission(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(observation_definition.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_retrieve_observation_definition_without_facility_as_user(self):
        """Retrieve observation definition without facility as any user should return 200."""
        observation_definition = self.create_observation_definition()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(observation_definition.external_id),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(observation_definition.external_id))

    # Test cases for update observation definition

    def test_update_observation_definition_as_superuser(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(observation_definition.external_id),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(get_response.data["slug"], update_data["slug"])
        self.assertEqual(get_response.data["category"], update_data["category"])
        self.assertEqual(get_response.data["status"], update_data["status"])

    def test_update_observation_definition_as_user_with_permission(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(observation_definition.external_id),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(get_response.data["slug"], update_data["slug"])
        self.assertEqual(get_response.data["category"], update_data["category"])
        self.assertEqual(get_response.data["status"], update_data["status"])

    def test_update_observation_definition_without_permission(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_update_observation_definition_without_facility_as_superuser(self):
        observation_definition = self.create_observation_definition()
        self.client.force_authenticate(user=self.superuser)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(observation_definition.external_id),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(get_response.data["slug"], update_data["slug"])
        self.assertEqual(get_response.data["category"], update_data["category"])
        self.assertEqual(get_response.data["status"], update_data["status"])

    def test_update_observation_definition_without_facility_as_user(self):
        observation_definition = self.create_observation_definition()
        self.client.force_authenticate(user=self.user)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_update_observation_definition_with_duplicate_slug(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        update_data = self.observation_definition_data.copy()
        update_data["slug"] = "heart-rate"
        response = self.client.put(
            self.get_detail_url(observation_definition.external_id),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Slug must be unique",
            str(response.data),
        )

    def test_update_observation_definition_with_invalid_permitted_data_type(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility
        )
        self.client.force_authenticate(user=self.superuser)
        invalid_question_types = ["group", "display", "url"]
        invalid_data = self.observation_definition_data.copy()
        invalid_data["permitted_data_type"] = choice(invalid_question_types)
        response = self.client.put(
            self.get_detail_url(observation_definition.external_id),
            invalid_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "permitted_data_type",
            str(response.data),
        )
        self.assertIn("Cannot create a definition with this type", str(response.data))

    # Test cases for list observation definitions

    def test_list_observation_definitions_with_facility_as_superuser(self):
        self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"facility": self.facility.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        for data in response.data["results"]:
            self.assertEqual(data["facility"]["id"], str(self.facility.external_id))

    def test_list_observation_definition_without_facility_as_superuser(self):
        self.create_observation_definition(slug="blood-pressure")
        self.create_observation_definition(slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        for data in response.data["results"]:
            self.assertIsNone(data["facility"])

    def test_list_observation_definitions_with_facility_as_user_with_permission(self):
        self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url, {"facility": self.facility.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        for data in response.data["results"]:
            self.assertEqual(data["facility"]["id"], str(self.facility.external_id))

    def test_list_observation_definitions_without_facility_as_user_with_permission(
        self,
    ):
        self.create_observation_definition(slug="blood-pressure")
        self.create_observation_definition(slug="heart-rate")
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        for data in response.data["results"]:
            self.assertIsNone(data["facility"])

    def test_list_observation_definitions_with_facility_without_permission(self):
        self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url, {"facility": self.facility.external_id}, format="json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_list_observation_definition_without_facility_without_permission(self):
        self.create_observation_definition(slug="blood-pressure")
        self.create_observation_definition(slug="heart-rate")
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, format="json")
        self.assertEqual(response.status_code, 200)
        for data in response.data["results"]:
            self.assertIsNone(data["facility"])

    def test_list_observation_definitions_with_invalid_facility(self):
        self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url, {"facility": "invalid-facility"}, format="json"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["errors"][0]["msg"], "Object not found")

    def test_list_observation_definition_with_category_filter(self):
        self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url,
            {
                "category": ObservationCategoryChoices.vital_signs.value,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        for data in response.data["results"]:
            self.assertEqual(
                data["category"], ObservationCategoryChoices.vital_signs.value
            )

    def test_list_observation_definition_with_status_filter(self):
        self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url,
            {
                "status": ObservationStatusChoices.active.value,
                "facility": self.facility.external_id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        for data in response.data["results"]:
            self.assertEqual(data["status"], ObservationStatusChoices.active.value)

    def test_list_observation_definition_with_title_filter(self):
        self.create_observation_definition(
            facility=self.facility, slug="blood-pressure", title="Blood Pressure"
        )
        self.create_observation_definition(
            facility=self.facility, slug="heart-rate", title="Heart Rate"
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.url,
            {"title": "Blood Pressure", "facility": self.facility.external_id},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "Blood Pressure")
