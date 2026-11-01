from django.urls import reverse

from care.emr.models.immunisation import ImmunizationRecommendation
from care.security.permissions.encounter import EncounterPermissions
from care.utils.tests.base import CareAPITestBase


class TestImmunizationRecommendationTree(CareAPITestBase):
    def setUp(self):
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        role = self.create_role_with_permissions(
            [EncounterPermissions.can_write_encounter_clinical_data.name]
        )
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.client.force_authenticate(self.user)
        self.url = reverse(
            "immunization-recommendation-create-tree",
            kwargs={"patient_external_id": self.patient.external_id},
        )
        self.data = {
            "patient": str(self.patient.external_id),
            "encounter": str(self.encounter.external_id),
            "root": {
                "is_group": True,
                "description": "Vaccination schedule",
                "children": [
                    {
                        "is_group": True,
                        "children": [
                            {
                                "is_group": False,
                                "codes": [{"system": "test", "code": "vaccine"}],
                                "due_date": "2026-01-15",
                            }
                        ],
                    }
                ],
            },
        }

    def test_create_tree_preserves_hierarchy_and_patient(self):
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, 200, response.json())
        root = ImmunizationRecommendation.objects.get(external_id=response.json()["id"])
        self.assertIsNone(root.parent)
        group = root.children.get()
        dose = group.children.get()
        self.assertEqual(str(dose.due_date), "2026-01-15")
        self.assertEqual(dose.codes[0]["code"], "vaccine")
        self.assertEqual(
            ImmunizationRecommendation.objects.filter(
                patient=self.patient,
                encounter=self.encounter,
                created_by=self.user,
                forecast_status="due",
            ).count(),
            3,
        )

    def test_invalid_later_dose_rolls_back_entire_tree(self):
        self.data["root"]["children"].append({"is_group": False})
        response = self.client.post(self.url, self.data, format="json")
        self.assertEqual(response.status_code, 400, response.json())
        self.assertIn("Codes are required", response.json()["errors"][0]["msg"])
        self.assertFalse(ImmunizationRecommendation.objects.exists())

    def test_rejects_patient_or_encounter_access_mismatch(self):
        other_patient = self.create_patient()
        with self.subTest("body patient differs from route"):
            self.data["patient"] = str(other_patient.external_id)
            response = self.client.post(self.url, self.data, format="json")
            self.assertEqual(response.status_code, 400)
        with self.subTest("encounter belongs to another patient"):
            other_url = reverse(
                "immunization-recommendation-create-tree",
                kwargs={"patient_external_id": other_patient.external_id},
            )
            response = self.client.post(other_url, self.data, format="json")
            self.assertEqual(response.status_code, 404)
        self.data["patient"] = str(self.patient.external_id)
        with self.subTest("user lacks clinical write permission"):
            self.client.force_authenticate(self.create_user())
            response = self.client.post(self.url, self.data, format="json")
            self.assertEqual(response.status_code, 403)
        with self.subTest("encounter is completed"):
            self.client.force_authenticate(self.user)
            self.encounter.status = "completed"
            self.encounter.save(update_fields=["status"])
            response = self.client.post(self.url, self.data, format="json")
            self.assertEqual(response.status_code, 403)
        self.assertFalse(ImmunizationRecommendation.objects.exists())
