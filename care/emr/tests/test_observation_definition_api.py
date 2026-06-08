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
            "slug_value": "blood-pressure",
            "category": ObservationCategoryChoices.vital_signs.value,
            "status": ObservationStatusChoices.active.value,
            "description": "Definition for measuring blood pressure",
            "code": {
                "system": "http://loinc.org",
                "code": "85354-9",
                "display": "Blood pressure panel with all children",
            },
            "permitted_data_type": QuestionType.quantity.value,
            "qualified_ranges": [],
            "facility": str(self.facility.external_id),
        }
        self.url = reverse("observation_definition-list")

    def get_detail_url(self, slug):
        return reverse(
            "observation_definition-detail",
            kwargs={
                "slug": slug,
            },
        )

    def get_metrics_url(self):
        return reverse("observation_definition-metrics")

    def create_observation_definition(self, slug=None, **kwargs):
        return baker.make(
            "ObservationDefinition",
            slug=f"f-{kwargs['facility'].external_id}-{slug}"
            if "facility" in kwargs
            else f"i-{slug}",
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
            self.get_detail_url(response.data["slug"]),
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
            self.get_detail_url(response.data["slug"]),
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
            self.get_detail_url(response.data["slug"]),
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

    def test_create_observation_definition_with_duplicate_slug_in_facility(self):
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
            "Slug already exists.",
            str(response.data),
        )

    def test_create_observation_definition_with_duplicate_slug_in_instance(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_observation_definition(slug="blood-pressure")
        self.observation_definition_data.pop("facility")
        response = self.client.post(
            self.url,
            self.observation_definition_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Slug already exists.",
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
            self.get_detail_url(observation_definition.slug),
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
            self.get_detail_url(observation_definition.slug),
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
            self.get_detail_url(observation_definition.slug),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_retrieve_observation_definition_without_facility_as_user(self):
        """Retrieve observation definition without facility as any user should return 200."""
        observation_definition = self.create_observation_definition()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(observation_definition.slug),
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(observation_definition.external_id))

    # Test cases for update observation definition

    def test_update_observation_definition_as_superuser(self):
        observation_definition = self.create_observation_definition(
            slug="blood-pressure", facility=self.facility
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug_value"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["slug"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(
            get_response.data["slug_config"]["slug_value"], update_data["slug_value"]
        )
        self.assertEqual(get_response.data["category"], update_data["category"])
        self.assertEqual(get_response.data["status"], update_data["status"])

    def test_update_observation_definition_as_user_with_permission(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility,
            slug="blood-pressure",
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug_value"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["slug"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(
            get_response.data["slug_config"]["slug_value"], update_data["slug_value"]
        )
        self.assertEqual(get_response.data["category"], update_data["category"])
        self.assertEqual(get_response.data["status"], update_data["status"])

    def test_update_observation_definition_without_permission(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility,
            slug="blood-pressure",
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug_value"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value

        response = self.client.put(
            self.get_detail_url(observation_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_update_observation_definition_without_facility_as_superuser(self):
        observation_definition = self.create_observation_definition(
            slug="blood-pressure",
        )
        self.client.force_authenticate(user=self.superuser)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug_value"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value
        update_data.pop("facility")
        response = self.client.put(
            self.get_detail_url(observation_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(response.data["slug"]),
            format="json",
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])
        self.assertEqual(
            get_response.data["slug_config"]["slug_value"], update_data["slug_value"]
        )
        self.assertEqual(get_response.data["category"], update_data["category"])
        self.assertEqual(get_response.data["status"], update_data["status"])

    def test_update_observation_definition_without_facility_as_user(self):
        observation_definition = self.create_observation_definition(
            slug="blood-pressure",
        )
        self.client.force_authenticate(user=self.user)
        update_data = self.observation_definition_data.copy()
        update_data["title"] = "Updated Blood Pressure"
        update_data["slug_value"] = "updated-blood-pressure"
        update_data["category"] = ObservationCategoryChoices.vital_signs.value
        update_data["status"] = ObservationStatusChoices.active.value
        update_data.pop("facility")

        response = self.client.put(
            self.get_detail_url(observation_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Access Denied to Observation Definition", str(response.data))

    def test_update_observation_definition_with_duplicate_slug_in_facility(self):
        observation_definition = self.create_observation_definition(
            facility=self.facility, slug="blood-pressure"
        )
        self.create_observation_definition(facility=self.facility, slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        update_data = self.observation_definition_data.copy()
        update_data["slug_value"] = "heart-rate"
        response = self.client.put(
            self.get_detail_url(observation_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Slug already exists.",
            str(response.data),
        )

    def test_update_observation_definition_with_duplicate_slug_in_instance(self):
        observation_definition = self.create_observation_definition(
            slug="blood-pressure"
        )
        self.create_observation_definition(slug="heart-rate")
        self.client.force_authenticate(user=self.superuser)
        update_data = self.observation_definition_data.copy()
        update_data["slug_value"] = "heart-rate"
        response = self.client.put(
            self.get_detail_url(observation_definition.slug),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(
            "Slug already exists.",
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
            self.get_detail_url(observation_definition.slug),
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
        self.assertEqual(
            response.data["errors"][0]["msg"], "No Facility matches the given query."
        )

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

    # Test cases for metrics

    def test_metrics_contains_expected_fields(self):
        """Test that the metrics endpoint returns expected fields."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_metrics_url(), format="json")

        self.assertEqual(response.status_code, 200)
        metric_names = [metric["name"] for metric in response.data]
        self.assertIn("encounter_tag", metric_names)
        self.assertIn("patient_age", metric_names)
        self.assertIn("patient_gender", metric_names)

    def test_metrics_encounter_tag_format(self):
        """Test that encounter_tag metrics have expected format."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_metrics_url(), format="json")

        self.assertEqual(response.status_code, 200)
        encounter_tag = next(
            (metric for metric in response.data if metric["name"] == "encounter_tag"),
            None,
        )
        self.assertIsNotNone(encounter_tag)
        self.assertEqual(encounter_tag["name"], "encounter_tag")
        self.assertEqual(encounter_tag["verbose_name"], "Encounter Tag")
        self.assertEqual(encounter_tag["context"], "encounter")
        self.assertEqual(encounter_tag["allowed_operations"], ["has_tag"])

    def test_metrics_patient_age_format(self):
        """Test that patient_age metrics have expected format."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_metrics_url(), format="json")

        self.assertEqual(response.status_code, 200)
        patient_age = next(
            (metric for metric in response.data if metric["name"] == "patient_age"),
            None,
        )
        self.assertIsNotNone(patient_age)
        self.assertEqual(patient_age["name"], "patient_age")
        self.assertEqual(patient_age["verbose_name"], "Patient Age")
        self.assertEqual(patient_age["context"], "patient")
        self.assertListEqual(
            patient_age["allowed_operations"], ["in_range", "equality"]
        )

    def test_metrics_patient_gender_format(self):
        """Test that patient_gender metrics have expected format."""
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.get_metrics_url(), format="json")

        self.assertEqual(response.status_code, 200)
        patient_gender = next(
            (metric for metric in response.data if metric["name"] == "patient_gender"),
            None,
        )
        self.assertIsNotNone(patient_gender)
        self.assertEqual(patient_gender["name"], "patient_gender")
        self.assertEqual(patient_gender["verbose_name"], "Patient Gender")
        self.assertEqual(patient_gender["context"], "patient")
        self.assertEqual(patient_gender["allowed_operations"], ["equality"])
        self.assertEqual(patient_gender["verbose_name"], "Patient Gender")
        self.assertEqual(patient_gender["context"], "patient")
        self.assertEqual(patient_gender["allowed_operations"], ["equality"])

    def test_metrics_without_permission(self):
        """Test that unauthorized users can access metrics."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_metrics_url(), format="json")

        self.assertEqual(response.status_code, 200)
        metric_names = [metric["name"] for metric in response.data]
        self.assertIn("encounter_tag", metric_names)
        self.assertIn("patient_age", metric_names)
        self.assertIn("patient_gender", metric_names)

    def test_metrics_with_permission(self):
        """Test that authorized users can access metrics."""
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.get_metrics_url(), format="json")

        self.assertEqual(response.status_code, 200)
        metric_names = [metric["name"] for metric in response.data]
        self.assertIn("encounter_tag", metric_names)
        self.assertIn("patient_age", metric_names)
        self.assertIn("patient_gender", metric_names)

    def _obs_def_data(self, slug_value, component=None, **kwargs):
        data = {
            "title": "Test Observation Definition",
            "status": ObservationStatusChoices.active.value,
            "description": "A test observation definition",
            "category": ObservationCategoryChoices.vital_signs.value,
            "code": {"system": "http://example.com", "code": "12345"},
            "permitted_data_type": QuestionType.decimal.value,
            "qualified_ranges": [
                {
                    "title": "Default",
                    "ranges": [
                        {
                            "interpretation": {"display": "Normal"},
                            "min": "0",
                            "max": "100",
                        }
                    ],
                }
            ],
            "facility": str(self.facility.external_id),
            "slug_value": slug_value,
            **kwargs,
        }
        if component is not None:
            data["component"] = component
        return data

    def _component_payload(self):
        return [
            {
                "code": {"system": "http://example.com", "code": "comp-1"},
                "permitted_data_type": QuestionType.decimal.value,
                "qualified_ranges": [
                    {
                        "title": "Component Range",
                        "ranges": [
                            {
                                "interpretation": {"display": "Normal"},
                                "min": "0",
                                "max": "50",
                            }
                        ],
                    }
                ],
            }
        ]

    def test_update_component_to_empty_list_clears_components(self):
        """
        Creating an observation definition with components and then
        updating with component=[] should clear the component list.
        """
        self.client.force_authenticate(user=self.superuser)
        create_data = self._obs_def_data(
            slug_value="clear-component-test",
            component=self._component_payload(),
        )
        create_resp = self.client.post(self.url, create_data, format="json")
        self.assertEqual(create_resp.status_code, 200)
        slug = create_resp.data["slug"]

        get_resp = self.client.get(self.get_detail_url(slug))
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(len(get_resp.data["component"]), 1)

        update_data = self._obs_def_data(
            slug_value="clear-component-test",
            component=[],
        )
        update_resp = self.client.put(
            self.get_detail_url(slug), update_data, format="json"
        )
        self.assertEqual(update_resp.status_code, 200)

        get_resp = self.client.get(self.get_detail_url(slug))
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.data["component"], [])
