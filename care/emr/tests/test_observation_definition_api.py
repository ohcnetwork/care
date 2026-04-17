from django.urls import reverse

from care.emr.resources.observation_definition.spec import (
    ObservationCategoryChoices,
    ObservationStatusChoices,
)
from care.emr.resources.questionnaire.spec import QuestionType
from care.utils.tests.base import CareAPITestBase


class TestObservationDefinitionViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.superuser = self.create_super_user(username="superuser")
        self.facility = self.create_facility(user=self.superuser)
        self.base_url = reverse("observation_definition-list")
        self.client.force_authenticate(user=self.superuser)

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

    def _detail_url(self, slug):
        return reverse("observation_definition-detail", kwargs={"slug": slug})

    def test_update_component_to_empty_list_clears_components(self):
        """
        Creating an observation definition with components and then
        updating with component=[] should clear the component list.
        """
        create_data = self._obs_def_data(
            slug_value="clear-component-test",
            component=self._component_payload(),
        )
        create_resp = self.client.post(self.base_url, create_data, format="json")
        self.assertEqual(create_resp.status_code, 200)
        slug = create_resp.data["slug"]

        get_resp = self.client.get(self._detail_url(slug))
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(len(get_resp.data["component"]), 1)

        update_data = self._obs_def_data(
            slug_value="clear-component-test",
            component=[],
        )
        update_resp = self.client.put(
            self._detail_url(slug), update_data, format="json"
        )
        self.assertEqual(update_resp.status_code, 200)

        get_resp = self.client.get(self._detail_url(slug))
        self.assertEqual(get_resp.status_code, 200)
        self.assertEqual(get_resp.data["component"], [])
