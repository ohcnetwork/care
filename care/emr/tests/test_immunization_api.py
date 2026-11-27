from django.urls import reverse
from model_bakery import baker

from care.emr.models.immunisation import Immunization, ImmunizationRecommendation
from care.emr.models.location import FacilityLocation
from care.emr.models.product import Product
from care.emr.resources.encounter.constants import StatusChoices
from care.security.permissions.immunization import ImmunizationPermissions
from care.utils.tests.base import CareAPITestBase


class TestImmunizationRecordViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.client.force_authenticate(self.user)
        self.code = {
            "system": "http://snomed.info/sct",
            "code": "1119349007",
            "display": "Vaccine product",
        }

    def list_url(self, patient=None):
        return reverse(
            "immunization-record-list",
            kwargs={"patient_external_id": (patient or self.patient).external_id},
        )

    def detail_url(self, record, patient=None):
        return reverse(
            "immunization-record-detail",
            kwargs={
                "patient_external_id": (patient or self.patient).external_id,
                "external_id": record.external_id,
            },
        )

    def grant_permissions(self, *permissions):
        role = self.create_role_with_permissions(list(permissions))
        self.attach_role_facility_organization_user(self.organization, self.user, role)

    def grant_access(self):
        self.grant_permissions(
            ImmunizationPermissions.can_read_immunization.name,
            ImmunizationPermissions.can_write_immunization.name,
        )

    def payload(self, **kwargs):
        return {
            "encounter": str(self.encounter.external_id),
            "status": "completed",
            "code": self.code,
            "primary_source": True,
            "administered_by": self.user.username,
            **kwargs,
        }

    def make_record(self, encounter=None, **kwargs):
        encounter = encounter or self.encounter
        data = {
            "encounter": encounter,
            "patient": encounter.patient,
            "facility": encounter.facility,
            "status": "completed",
            "code": self.code,
            "primary_source": True,
            "administered_by": self.user,
            **kwargs,
        }
        return baker.make(Immunization, **data)

    def make_recommendation(self, patient=None):
        return baker.make(
            ImmunizationRecommendation,
            patient=patient or self.patient,
            codes=[self.code],
            is_group=False,
            forecast_status="due",
        )

    def other_encounter(self, patient=None):
        return self.create_encounter(
            patient=patient or self.patient,
            facility=self.facility,
            organization=self.create_facility_organization(facility=self.facility),
        )

    def test_create_with_optional_relationships_omitted(self):
        self.grant_access()
        payload = self.payload()
        payload.pop("administered_by")
        response = self.client.post(self.list_url(), payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        record = Immunization.objects.get(external_id=response.data["id"])
        self.assertEqual(record.encounter, self.encounter)
        self.assertEqual(record.patient, self.patient)
        self.assertEqual(record.facility, self.facility)
        self.assertEqual(record.created_by, self.user)
        self.assertIsNone(record.recommendation)
        self.assertIsNone(record.product)
        self.assertIsNone(record.location)
        self.assertIsNone(record.administered_by)
        self.assertIsNone(response.data["administered_by"])
        response = self.client.get(self.detail_url(record))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["administered_by"])
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(record.external_id)],
        )
        self.assertIsNone(response.data["results"][0]["administered_by"])

    def test_create_with_explicitly_null_administered_by(self):
        self.grant_access()
        response = self.client.post(
            self.list_url(), self.payload(administered_by=None), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["administered_by"])
        record = Immunization.objects.get(external_id=response.data["id"])
        self.assertIsNone(record.administered_by)

    def test_patch_preserves_administered_by_until_explicitly_cleared(self):
        self.grant_access()
        record = self.make_record()
        response = self.client.patch(
            self.detail_url(record), {"note": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["administered_by"]["username"], self.user.username
        )
        record.refresh_from_db()
        self.assertEqual(record.administered_by, self.user)
        response = self.client.patch(
            self.detail_url(record), {"administered_by": None}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIsNone(response.data["administered_by"])
        record.refresh_from_db()
        self.assertIsNone(record.administered_by)

    def test_create_and_retrieve_optional_relationships(self):
        self.grant_access()
        recommendation = self.make_recommendation()
        product = baker.make(Product, facility=self.facility)
        location = baker.make(FacilityLocation, facility=self.facility)
        relationships = {
            "recommendation": str(recommendation.external_id),
            "product": str(product.external_id),
            "location": str(location.external_id),
            "administered_by": self.user.username,
        }
        response = self.client.post(
            self.list_url(), self.payload(**relationships), format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        for field in ("recommendation", "product", "location"):
            self.assertEqual(response.data[field], relationships[field])
        self.assertEqual(
            response.data["administered_by"]["username"], self.user.username
        )
        record = Immunization.objects.get(external_id=response.data["id"])
        response = self.client.get(self.detail_url(record))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["encounter"], str(self.encounter.external_id))
        for field in ("recommendation", "product", "location"):
            self.assertEqual(response.data[field], relationships[field])
        self.assertEqual(
            response.data["administered_by"]["username"], self.user.username
        )

    def test_patch_preserves_omitted_relationships_and_clears_explicit_null(self):
        self.grant_access()
        recommendation = self.make_recommendation()
        record = self.make_record(recommendation=recommendation, note="Original")
        response = self.client.patch(
            self.detail_url(record), {"note": "Updated"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        record.refresh_from_db()
        self.assertEqual(record.recommendation, recommendation)
        self.assertEqual(record.note, "Updated")
        self.assertEqual(record.code, self.code)
        self.assertEqual(record.updated_by, self.user)
        response = self.client.patch(
            self.detail_url(record), {"recommendation": None}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        record.refresh_from_db()
        self.assertIsNone(record.recommendation)

    def test_no_permissions_denies_reads_and_writes(self):
        record = self.make_record()
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)
        self.assertEqual(self.client.get(self.detail_url(record)).status_code, 403)
        response = self.client.post(self.list_url(), self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.patch(
            self.detail_url(record), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        record.refresh_from_db()
        self.assertIsNone(record.note)

    def test_read_permission_does_not_allow_writes(self):
        self.grant_permissions(ImmunizationPermissions.can_read_immunization.name)
        record = self.make_record()
        self.assertEqual(self.client.get(self.list_url()).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url(record)).status_code, 200)
        response = self.client.post(self.list_url(), self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.patch(
            self.detail_url(record), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_write_permission_allows_updates_without_read_permission(self):
        self.grant_permissions(ImmunizationPermissions.can_write_immunization.name)
        record = self.make_record()
        self.assertEqual(self.client.get(self.list_url()).status_code, 403)
        self.assertEqual(self.client.get(self.detail_url(record)).status_code, 403)
        response = self.client.patch(
            self.detail_url(record), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_cross_patient_create_detail_and_update_are_rejected(self):
        self.grant_access()
        other_patient = self.create_patient()
        response = self.client.post(
            self.list_url(other_patient), self.payload(), format="json"
        )
        self.assertEqual(response.status_code, 404, response.data)
        self.assertFalse(Immunization.objects.exists())
        record = self.make_record()
        self.assertEqual(
            self.client.get(self.detail_url(record, other_patient)).status_code, 404
        )
        response = self.client.patch(
            self.detail_url(record, other_patient), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 404, response.data)

    def test_recommendation_must_belong_to_record_patient(self):
        self.grant_access()
        recommendation = self.make_recommendation(patient=self.create_patient())
        response = self.client.post(
            self.list_url(),
            self.payload(recommendation=str(recommendation.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 404, response.data)
        self.assertFalse(Immunization.objects.exists())

    def test_product_and_location_must_belong_to_encounter_facility(self):
        self.grant_access()
        other_facility = self.create_facility(user=self.user)
        product = baker.make(Product, facility=other_facility)
        location = baker.make(FacilityLocation, facility=other_facility)
        for field, value in [("product", product), ("location", location)]:
            with self.subTest(field=field):
                response = self.client.post(
                    self.list_url(),
                    self.payload(**{field: str(value.external_id)}),
                    format="json",
                )
                self.assertEqual(response.status_code, 404, response.data)
        self.assertFalse(Immunization.objects.exists())

    def test_encounter_filter_cannot_refer_to_another_patient(self):
        self.grant_access()
        self.make_record()
        other_encounter = self.other_encounter(patient=self.create_patient())
        response = self.client.get(
            self.list_url(), {"encounter": str(other_encounter.external_id)}
        )
        self.assertEqual(response.status_code, 404, response.data)

    def test_closed_encounter_read_uses_encounter_permission_fallback(self):
        self.grant_permissions(ImmunizationPermissions.can_read_immunization.name)
        record = self.make_record()
        hidden_encounter = self.other_encounter()
        hidden = self.make_record(encounter=hidden_encounter)
        self.encounter.status = StatusChoices.completed.value
        self.encounter.save(update_fields=["status"])

        self.assertEqual(self.client.get(self.list_url()).status_code, 403)
        response = self.client.get(
            self.list_url(), {"encounter": str(self.encounter.external_id)}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(record.external_id)],
        )
        self.assertEqual(self.client.get(self.detail_url(record)).status_code, 200)
        self.assertEqual(self.client.get(self.detail_url(hidden)).status_code, 403)
        response = self.client.get(
            self.list_url(), {"encounter": str(hidden_encounter.external_id)}
        )
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.get(
            self.detail_url(hidden), {"encounter": str(self.encounter.external_id)}
        )
        self.assertEqual(response.status_code, 404, response.data)
        response = self.client.get(
            self.detail_url(record), {"encounter": str(hidden_encounter.external_id)}
        )
        self.assertEqual(response.status_code, 404, response.data)

    def test_malformed_encounter_query_returns_not_found(self):
        self.grant_access()
        record = self.make_record()
        for url in [self.list_url(), self.detail_url(record)]:
            with self.subTest(url=url):
                response = self.client.get(url, {"encounter": "not-a-uuid"})
                self.assertEqual(response.status_code, 404, response.data)

    def test_retrieve_and_update_use_objects_encounter_permissions(self):
        self.grant_access()
        hidden = self.make_record(encounter=self.other_encounter())
        # A patient-wide read may expose this patient's history, while writes
        # still require access to the encounter that recorded the immunization.
        response = self.client.patch(
            self.detail_url(hidden), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.get(
            self.detail_url(hidden), {"encounter": str(self.encounter.external_id)}
        )
        self.assertEqual(response.status_code, 404, response.data)

    def test_encounter_and_patient_cannot_be_changed_on_update(self):
        self.grant_access()
        record = self.make_record()
        other_encounter = self.other_encounter(patient=self.create_patient())
        response = self.client.patch(
            self.detail_url(record),
            {
                "encounter": str(other_encounter.external_id),
                "patient": str(other_encounter.patient.external_id),
                "note": "Updated",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        record.refresh_from_db()
        self.assertEqual(record.patient, self.patient)
        self.assertEqual(record.encounter, self.encounter)

    def test_closed_encounter_denies_create_and_update(self):
        self.grant_access()
        record = self.make_record()
        self.encounter.status = StatusChoices.completed.value
        self.encounter.save(update_fields=["status"])
        response = self.client.post(self.list_url(), self.payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        response = self.client.patch(
            self.detail_url(record), {"note": "Changed"}, format="json"
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_status_filter_and_patient_scope(self):
        self.grant_access()
        completed = self.make_record()
        self.make_record(status="not_done")
        other_encounter = self.other_encounter(patient=self.create_patient())
        self.make_record(encounter=other_encounter)
        response = self.client.get(self.list_url(), {"status": "completed"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(completed.external_id)],
        )
