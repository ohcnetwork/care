"""Tests for the inbound (BPP) referral flow: init/confirm -> ResourceRequest."""

from django.test import override_settings
from django.urls import reverse

from care.beckn.builders.referral import build_on_init
from care.emr.models import Patient
from care.emr.models.resource_request import ResourceRequest
from care.emr.resources.resource_request.spec import CategoryChoices, StatusChoices
from care.utils.tests.base import CareAPITestBase

PATIENT_PARTICIPANT = {
    "id": "participant-patient-1",
    "descriptor": {"name": "Jo Patient"},
    "participantAttributes": {"participantRole": "PATIENT", "gender": "MALE"},
}


@override_settings(BECKN_SYSTEM_USERNAME="beckn_sys")
class ReferralFlowTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="beckn_sys")
        self.facility = self.create_facility(user=self.user)

    def _contract(
        self, coordination_id, contract_id=None, participants=None, status=None
    ):
        contract = {
            "descriptor": {"name": "Cardiology referral"},
            "contractAttributes": {
                "@type": "hrf:HealthReferral",
                "facilityId": str(self.facility.external_id),
                "coordinationId": coordination_id,
                "clinicalUrgencyTier": "ROUTINE",
            },
            "participants": (
                [PATIENT_PARTICIPANT] if participants is None else participants
            ),
        }
        if contract_id:
            contract["id"] = contract_id
        if status:
            contract["status"] = {"code": status}
        return contract

    def _post(self, action, contract, transaction_id="txn-1", **context):
        return self.client.post(
            reverse("beckn-bpp-webhook-action", kwargs={"action": action}),
            {
                "context": {
                    "action": action,
                    "transactionId": transaction_id,
                    **context,
                },
                "message": {"contract": contract},
            },
            format="json",
        )

    def _assert_ack(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"]["ack"]["status"], "ACK")

    def _assert_nack(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"]["ack"]["status"], "NACK")

    def test_confirm_without_init_creates_approved_referral(self):
        """A BAP that skips ``init`` still gets a referral (Care's BAP never sends one)."""
        self._assert_ack(self._post("confirm", self._contract("COORD-1")))

        referrals = ResourceRequest.objects.filter(origin_facility=self.facility)
        self.assertEqual(referrals.count(), 1)
        referral = referrals.first()
        self.assertEqual(referral.status, StatusChoices.approved.value)
        self.assertEqual(referral.extensions["beckn"]["coordinationId"], "COORD-1")
        self.assertIsNotNone(referral.related_patient_id)

    def test_confirm_resolves_by_coordination_id(self):
        """``confirm`` finds the referral created at ``init`` without a contract id."""
        self._assert_ack(self._post("init", self._contract("COORD-2")))
        referral = ResourceRequest.objects.get(origin_facility=self.facility)
        self.assertEqual(referral.status, StatusChoices.pending.value)

        self._assert_ack(self._post("confirm", self._contract("COORD-2")))

        self.assertEqual(
            ResourceRequest.objects.filter(origin_facility=self.facility).count(), 1
        )
        referral.refresh_from_db()
        self.assertEqual(referral.status, StatusChoices.approved.value)

    def test_confirm_resolves_by_contract_id(self):
        """The contract id published on ``on_init`` still resolves the referral."""
        self._assert_ack(self._post("init", self._contract("COORD-3")))
        referral = ResourceRequest.objects.get(origin_facility=self.facility)

        contract = self._contract("", contract_id=str(referral.external_id))
        self._assert_ack(self._post("confirm", contract))

        self.assertEqual(
            ResourceRequest.objects.filter(origin_facility=self.facility).count(), 1
        )
        referral.refresh_from_db()
        self.assertEqual(referral.status, StatusChoices.approved.value)

    def test_init_retry_updates_instead_of_duplicating(self):
        """A retried ``init`` is the same referral, not a second one."""
        self._assert_ack(self._post("init", self._contract("COORD-4")))
        self._assert_ack(self._post("init", self._contract("COORD-4")))

        self.assertEqual(
            ResourceRequest.objects.filter(origin_facility=self.facility).count(), 1
        )
        self.assertEqual(Patient.objects.count(), 1)

    def test_init_retry_does_not_undo_an_approval(self):
        """An init arriving after the confirm must not pull the referral back."""
        self._assert_ack(self._post("init", self._contract("COORD-5")))
        self._assert_ack(self._post("confirm", self._contract("COORD-5")))

        self._assert_ack(self._post("init", self._contract("COORD-5")))

        referral = ResourceRequest.objects.get(origin_facility=self.facility)
        self.assertEqual(referral.status, StatusChoices.approved.value)

    def test_confirm_requires_an_active_contract(self):
        self._assert_nack(
            self._post("confirm", self._contract("COORD-6", status="DRAFT"))
        )
        self.assertFalse(
            ResourceRequest.objects.filter(origin_facility=self.facility).exists()
        )

    def test_confirm_refused_once_the_referral_has_moved_on(self):
        self._assert_ack(self._post("init", self._contract("COORD-7")))
        referral = ResourceRequest.objects.get(origin_facility=self.facility)
        referral.status = StatusChoices.cancelled.value
        referral.save(update_fields=["status"])

        self._assert_nack(self._post("confirm", self._contract("COORD-7")))

        referral.refresh_from_db()
        self.assertEqual(referral.status, StatusChoices.cancelled.value)

    def test_confirm_from_another_bap_is_refused(self):
        """The webhook is unauthenticated, so the bapId is the only owner check."""
        self._assert_ack(
            self._post("init", self._contract("COORD-8"), bapId="bap-a.example.org")
        )

        self._assert_nack(
            self._post("confirm", self._contract("COORD-8"), bapId="bap-b.example.org")
        )

        referral = ResourceRequest.objects.get(origin_facility=self.facility)
        self.assertEqual(referral.status, StatusChoices.pending.value)

    def test_a_bap_is_recorded_on_first_contact(self):
        """A referral created without a bapId still learns one from the confirm."""
        self._assert_ack(self._post("init", self._contract("COORD-10")))

        self._assert_ack(
            self._post("confirm", self._contract("COORD-10"), bapId="bap-a.example.org")
        )

        referral = ResourceRequest.objects.get(origin_facility=self.facility)
        self.assertEqual(referral.extensions["beckn"]["bapId"], "bap-a.example.org")

    def test_referral_without_a_patient_is_refused(self):
        self._assert_nack(
            self._post("init", self._contract("COORD-9", participants=[]))
        )
        self.assertFalse(
            ResourceRequest.objects.filter(origin_facility=self.facility).exists()
        )
        self.assertEqual(Patient.objects.count(), 0)

    def test_referring_contact_number_is_normalised_or_dropped(self):
        for telecom, expected in (
            ("9876543210", "+919876543210"),
            ("tel:+91 98765 43210", "+919876543210"),
            ("ask at reception", ""),
        ):
            with self.subTest(telecom=telecom):
                ResourceRequest.objects.filter(origin_facility=self.facility).delete()
                referrer = {
                    "descriptor": {"name": "Dr Referrer"},
                    "participantAttributes": {
                        "participantRole": "REFERRER",
                        "telecom": telecom,
                    },
                }
                self._assert_ack(
                    self._post(
                        "init",
                        self._contract(
                            f"COORD-{telecom}",
                            participants=[PATIENT_PARTICIPANT, referrer],
                        ),
                    )
                )
                referral = ResourceRequest.objects.get(origin_facility=self.facility)
                self.assertEqual(referral.referring_facility_contact_number, expected)

    def test_callback_publishes_the_referral_as_contract_id(self):
        referral = ResourceRequest.objects.create(
            origin_facility=self.facility,
            title="ref",
            status=StatusChoices.pending.value,
            category=CategoryChoices.other.value,
            created_by=self.user,
            updated_by=self.user,
        )
        payload = build_on_init({}, {"contract": {}}, referral)
        self.assertEqual(
            payload["message"]["contract"]["id"], str(referral.external_id)
        )
