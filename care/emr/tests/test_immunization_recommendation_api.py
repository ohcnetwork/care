from datetime import date

from django.urls import reverse
from model_bakery import baker

from care.emr.models.immunisation import ImmunizationPolicy, ImmunizationRecommendation
from care.security.permissions.immunization import ImmunizationPermissions
from care.utils.tests.base import CareAPITestBase


class TestImmunizationRecommendationAPI(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.client.force_authenticate(self.user)
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.code = {
            "system": "http://test.care/vaccine",
            "code": "vaccine",
            "display": "Vaccine",
        }
        self.url = reverse(
            "immunization-recommendation-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )
        self.apply_url = reverse(
            "immunization-recommendation-apply-policy",
            kwargs={"patient_external_id": self.patient.external_id},
        )

    def detail_url(self, recommendation, **query):
        url = reverse(
            "immunization-recommendation-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": recommendation.external_id,
            },
        )
        if query:
            url += "?" + "&".join(f"{key}={value}" for key, value in query.items())
        return url

    def make_recommendation(self, **kwargs):
        fields = {
            "patient": self.patient,
            "is_group": False,
            "forecast_status": "due",
            "codes": [self.code],
        }
        fields.update(kwargs)
        return baker.make(ImmunizationRecommendation, **fields)

    def create_data(self, **kwargs):
        return {
            "patient": str(self.patient.external_id),
            "is_group": False,
            "forecast_status": "due",
            "codes": [self.code],
            **kwargs,
        }

    def make_policy(self, **kwargs):
        fields = {
            "name": "Vaccine schedule",
            "policy_template": {
                "is_group": True,
                "description": "Schedule",
                "children": [
                    {
                        "is_group": False,
                        "codes": [self.code],
                        "earliest_date": 0,
                        "due_date": 7,
                        "overdue_date": 14,
                        "dose_number": "1",
                    },
                    {
                        "is_group": True,
                        "description": "Later doses",
                        "children": [
                            {
                                "is_group": False,
                                "codes": [self.code],
                                "due_date": 28,
                                "dose_number": "2",
                            }
                        ],
                    },
                ],
            },
        }
        fields.update(kwargs)
        return baker.make(ImmunizationPolicy, **fields)

    def apply_data(self, policy, **kwargs):
        return {
            "policy": str(policy.external_id),
            "reference_date": "2026-01-01",
            **kwargs,
        }

    def test_create_recommendation_and_patch_without_resending_codes(self):
        response = self.client.post(self.url, self.create_data(), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        recommendation = ImmunizationRecommendation.objects.get(
            external_id=response.data["id"]
        )
        self.assertEqual(response.data["patient"], str(self.patient.external_id))
        self.assertIsNone(response.data["parent"])
        response = self.client.patch(
            self.detail_url(recommendation), {"description": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        recommendation.refresh_from_db()
        self.assertEqual(recommendation.description, "Updated")
        self.assertEqual(recommendation.forecast_status, "due")
        self.assertEqual(recommendation.codes, [self.code])

    def test_empty_codes_rejected_for_individual_recommendation(self):
        response = self.client.post(self.url, self.create_data(codes=[]), format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ImmunizationRecommendation.objects.exists())

    def test_nested_patient_and_body_must_match(self):
        other_patient = self.create_patient()
        response = self.client.post(
            self.url,
            self.create_data(patient=str(other_patient.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ImmunizationRecommendation.objects.exists())

    def test_wrong_patient_encounter_is_rejected(self):
        other_patient = self.create_patient()
        encounter = self.create_encounter(
            patient=other_patient,
            facility=self.facility,
            organization=self.organization,
        )
        response = self.client.post(
            self.url,
            self.create_data(encounter=str(encounter.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 404)

    def test_parent_must_be_a_group_in_the_same_patient(self):
        nongroup = self.make_recommendation()
        other_group = self.make_recommendation(
            patient=self.create_patient(), is_group=True
        )
        for parent in [nongroup, other_group]:
            with self.subTest(parent=parent.external_id):
                response = self.client.post(
                    self.url,
                    self.create_data(parent=str(parent.external_id)),
                    format="json",
                )
                self.assertEqual(response.status_code, 404)

    def test_parent_encounter_must_match(self):
        parent = self.make_recommendation(is_group=True, encounter=self.encounter)
        response = self.client.post(
            self.url, self.create_data(parent=str(parent.external_id)), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_patient_scoping_and_encounter_filters_apply_to_detail(self):
        own = self.make_recommendation(encounter=self.encounter)
        other = self.make_recommendation(patient=self.create_patient())
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(own.external_id)]
        )
        self.assertEqual(self.client.get(self.detail_url(other)).status_code, 404)
        other_encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        url = self.detail_url(own, encounter=other_encounter.external_id)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(
            self.client.patch(
                url, {"description": "Hidden"}, format="json"
            ).status_code,
            404,
        )

    def test_closed_encounter_read_permission_is_scoped(self):
        self.encounter.status = "completed"
        self.encounter.save()
        user = self.create_user()
        role = self.create_role_with_permissions(
            [ImmunizationPermissions.can_read_immunization_recommendation.name]
        )
        self.attach_role_facility_organization_user(self.organization, user, role)
        own = self.make_recommendation(encounter=self.encounter)
        self.make_recommendation()
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        response = self.client.get(
            self.url, {"encounter": str(self.encounter.external_id)}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [row["id"] for row in response.data["results"]], [str(own.external_id)]
        )

    def test_unauthorized_operations_do_not_write(self):
        recommendation = self.make_recommendation()
        policy = self.make_policy()
        self.client.force_authenticate(self.create_user())
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(
            self.client.get(self.detail_url(recommendation)).status_code, 403
        )
        self.assertEqual(
            self.client.post(self.url, self.create_data(), format="json").status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                self.detail_url(recommendation),
                {"description": "Denied"},
                format="json",
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                self.apply_url, self.apply_data(policy), format="json"
            ).status_code,
            403,
        )
        self.assertEqual(ImmunizationRecommendation.objects.count(), 1)

    def test_apply_policy_creates_nested_tree_with_dates_and_audit_users(self):
        policy = self.make_policy()
        response = self.client.post(
            self.apply_url,
            self.apply_data(policy, encounter=str(self.encounter.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(len(response.data), 4)
        root, first, group, second = [
            ImmunizationRecommendation.objects.get(external_id=row["id"])
            for row in response.data
        ]
        self.assertIsNone(root.parent)
        self.assertEqual(first.parent, root)
        self.assertEqual(group.parent, root)
        self.assertEqual(second.parent, group)
        self.assertEqual(first.earliest_date, date(2026, 1, 1))
        self.assertEqual(first.due_date, date(2026, 1, 8))
        self.assertEqual(first.overdue_date, date(2026, 1, 15))
        self.assertEqual(second.due_date, date(2026, 1, 29))
        self.assertEqual(response.data[3]["parent"], str(group.external_id))
        for recommendation in [root, first, group, second]:
            self.assertEqual(recommendation.patient, self.patient)
            self.assertEqual(recommendation.encounter, self.encounter)
            self.assertEqual(recommendation.forecast_status, "due")
            self.assertEqual(recommendation.created_by, self.user)
            self.assertEqual(recommendation.updated_by, self.user)

    def test_apply_policy_can_attach_to_existing_group(self):
        parent = self.make_recommendation(is_group=True)
        policy = self.make_policy()
        response = self.client.post(
            self.apply_url,
            self.apply_data(policy, parent=str(parent.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        root = ImmunizationRecommendation.objects.get(
            external_id=response.data[0]["id"]
        )
        self.assertEqual(root.parent, parent)

    def test_apply_policy_rejects_wrong_facility(self):
        policy = self.make_policy(facility=self.create_facility(user=self.user))
        response = self.client.post(
            self.apply_url,
            self.apply_data(policy, encounter=str(self.encounter.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ImmunizationRecommendation.objects.exists())

    def test_apply_policy_requires_policy_read_access(self):
        policy = self.make_policy(facility=self.facility)
        user = self.create_user()
        role = self.create_role_with_permissions(
            [ImmunizationPermissions.can_write_immunization_recommendation.name]
        )
        self.attach_role_facility_organization_user(self.organization, user, role)
        self.client.force_authenticate(user)
        response = self.client.post(
            self.apply_url,
            self.apply_data(policy, encounter=str(self.encounter.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ImmunizationRecommendation.objects.exists())

    def test_apply_policy_requires_a_reference_date(self):
        policy = self.make_policy()
        response = self.client.post(
            self.apply_url, {"policy": str(policy.external_id)}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ImmunizationRecommendation.objects.exists())

    def test_invalid_policy_cannot_create_recommendations(self):
        policy = self.make_policy(policy_template={"is_group": False})
        response = self.client.post(
            self.apply_url, self.apply_data(policy), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ImmunizationRecommendation.objects.exists())

    def test_policy_date_overflow_rolls_back_the_whole_tree(self):
        policy = self.make_policy()
        policy.policy_template["children"][1]["children"][0]["due_date"] = 10**20
        policy.save()
        response = self.client.post(
            self.apply_url, self.apply_data(policy), format="json"
        )
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(ImmunizationRecommendation.objects.exists())
