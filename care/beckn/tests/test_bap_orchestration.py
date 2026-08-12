"""Tests for the Care-as-BAP Beckn orchestration (Redis-backed discover/select/
confirm) and the appointment -> referral completion hook."""

import datetime
import json
from types import SimpleNamespace

from django.test import override_settings
from django.urls import reverse

from care.beckn.services import txn_store
from care.beckn.services.flows import FlowError, get_adapter
from care.beckn.services.identifiers import ABHA_IDENTIFIER_SYSTEM
from care.beckn.tasks import complete_referral_for_booking
from care.emr.models.patient import PatientIdentifier, PatientIdentifierConfig
from care.emr.models.resource_request import ResourceRequest
from care.emr.resources.resource_request.spec import CategoryChoices, StatusChoices
from care.utils.tests.base import CareAPITestBase


class TxnStoreTests(CareAPITestBase):
    # Every test works on a transaction id of its own, so the store is never
    # cleared: the cache is one shared Redis database and flushing it would wipe
    # the transactions of every other test process under --parallel.

    def test_create_and_advance_status(self):
        record = txn_store.create_transaction("consultation")
        tid = record["transactionId"]
        self.assertEqual(record["status"], txn_store.STATUS_DISCOVER)
        self.assertEqual(record["serviceType"], "consultation")

        txn_store.record_request(tid, "discover", {"x": 1})
        self.assertEqual(txn_store.get_transaction(tid)["status"], "DISCOVER")

        txn_store.record_response(tid, "on_discover", {"y": 2})
        rec = txn_store.get_transaction(tid)
        self.assertEqual(rec["status"], "ON_DISCOVER")
        # The payloads live under their own keys; the record only lists which
        # actions have been recorded.
        self.assertEqual(rec["actions"], ["DISCOVER", "ON_DISCOVER"])
        self.assertEqual(txn_store.get_action(tid, "on_discover"), {"y": 2})
        self.assertEqual(txn_store.get_action(tid, "DISCOVER"), {"x": 1})

    def test_set_routing_merges_and_drops_none(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        txn_store.set_routing(tid, {"bppUri": "http://bpp", "bppId": None})
        self.assertEqual(
            txn_store.get_transaction(tid)["routing"], {"bppUri": "http://bpp"}
        )

    def test_set_resource_request(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        txn_store.set_resource_request(tid, "rr-123")
        self.assertEqual(txn_store.get_transaction(tid)["resourceRequestId"], "rr-123")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(txn_store.get_transaction("does-not-exist"))


class FlowAdapterTests(CareAPITestBase):
    def test_registry_lookup(self):
        self.assertEqual(get_adapter("consultation").service_type, "consultation")
        self.assertEqual(get_adapter("APPOINTMENT").service_type, "appointment")
        with self.assertRaises(FlowError):
            get_adapter("nope")

    def test_consultation_payloads(self):
        adapter = get_adapter("consultation")

        discover = adapter.build_discover("t1", {}, {"specialty": "cardiology"})
        self.assertEqual(discover["context"]["action"], "discover")
        self.assertEqual(discover["context"]["transactionId"], "t1")

        select = adapter.build_select("t1", {}, {}, {"offerId": "offer-1"})
        self.assertEqual(select["context"]["action"], "select")
        self.assertEqual(
            select["message"]["contract"]["commitments"][0]["offer"]["id"], "offer-1"
        )

        with self.assertRaises(FlowError):
            adapter.build_select("t1", {}, {}, {})

        confirm = adapter.build_confirm(
            "t1", {}, {}, {"offerId": "offer-1", "patientName": "Jo"}
        )
        self.assertEqual(confirm["context"]["action"], "confirm")
        self.assertEqual(
            confirm["message"]["contract"]["participants"][0]["descriptor"]["name"],
            "Jo",
        )

    def test_routing_overrides_bpp_identifiers(self):
        adapter = get_adapter("consultation")
        routing = {"bppId": "bpp-x", "bppUri": "http://bpp-x"}
        select = adapter.build_select("t1", routing, {}, {"offerId": "o"})
        self.assertEqual(select["context"]["bppId"], "bpp-x")
        self.assertEqual(select["context"]["bppUri"], "http://bpp-x")


@override_settings(BECKN_SYSTEM_USERNAME="beckn_sys")
class BAPReceiverTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="beckn_sys")
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()

    def _post(self, action, body):
        return self.client.post(
            reverse("beckn-bap-receiver-action", kwargs={"action": action}),
            body,
            format="json",
        )

    def test_on_discover_records_response_and_routing(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        body = {
            "context": {
                "action": "on_discover",
                "transactionId": tid,
                "bppId": "bpp1",
                "bppUri": "http://bpp1",
            },
            "message": {"catalogs": []},
        }
        response = self._post("on_discover", body)
        self.assertEqual(response.status_code, 200)
        rec = txn_store.get_transaction(tid)
        self.assertEqual(rec["status"], "ON_DISCOVER")
        self.assertEqual(rec["routing"]["bppUri"], "http://bpp1")

    def test_on_confirm_creates_referral(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        txn_store.set_patient(
            tid,
            {
                "facility": str(self.facility.external_id),
                "patient": str(self.patient.external_id),
                "title": "Cardio referral",
                "reason": "chest pain",
                "category": CategoryChoices.other.value,
            },
        )
        body = {
            "context": {"action": "on_confirm", "transactionId": tid},
            "message": {"contract": {"status": {"code": "ACTIVE"}}},
        }
        response = self._post("on_confirm", body)
        self.assertEqual(response.status_code, 200)

        rr = ResourceRequest.objects.filter(
            origin_facility=self.facility, title="Cardio referral"
        ).first()
        self.assertIsNotNone(rr)
        self.assertEqual(rr.status, StatusChoices.approved.value)
        self.assertEqual(rr.related_patient_id, self.patient.id)

        rec = txn_store.get_transaction(tid)
        self.assertEqual(rec["status"], "ON_CONFIRM")
        self.assertEqual(rec["resourceRequestId"], str(rr.external_id))

    def test_unknown_transaction_still_acks(self):
        body = {
            "context": {"action": "on_confirm", "transactionId": "unknown"},
            "message": {},
        }
        response = self._post("on_confirm", body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["message"]["ack"]["status"], "ACK")


# An empty caller url keeps the action endpoints from posting to a real network
# adapter; the payload Care built is still recorded on the transaction.
@override_settings(BECKN_SYSTEM_USERNAME="beckn_sys", BECKN_BAP_CALLER_URL="")
class BPPRoutingTests(CareAPITestBase):
    """``discover`` is a broadcast, so the chosen provider must stay unambiguous."""

    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="beckn_sys")
        self.client.force_authenticate(self.user)

    def _answer_discover(self, transaction_id, bpp_id):
        return self.client.post(
            reverse("beckn-bap-receiver-action", kwargs={"action": "on_discover"}),
            {
                "context": {
                    "action": "on_discover",
                    "transactionId": transaction_id,
                    "bppId": bpp_id,
                    "bppUri": f"http://{bpp_id}",
                },
                "message": {"catalogs": []},
            },
            format="json",
        )

    def _select(self, transaction_id, context=None):
        body = {
            "transactionId": transaction_id,
            "message": {"contract": {"status": {"code": "DRAFT"}}},
        }
        if context:
            body["context"] = context
        return self.client.post(
            reverse("beckn-bap-action", kwargs={"action": "select"}),
            body,
            format="json",
        )

    def test_the_only_provider_that_answered_is_used(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        self._answer_discover(tid, "bpp-a")

        self.assertEqual(self._select(tid).status_code, 202)

        sent = txn_store.get_action(tid, "SELECT")
        self.assertEqual(sent["context"]["bppId"], "bpp-a")
        self.assertEqual(sent["context"]["bppUri"], "http://bpp-a")

    def test_select_must_name_the_provider_when_several_answered(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        self._answer_discover(tid, "bpp-a")
        self._answer_discover(tid, "bpp-b")

        response = self._select(tid)
        self.assertEqual(response.status_code, 400)
        self.assertIn("bppId", response.data["detail"])

        response = self._select(tid, context={"bppId": "bpp-a"})
        self.assertEqual(response.status_code, 202)
        sent = txn_store.get_action(tid, "SELECT")
        self.assertEqual(sent["context"]["bppId"], "bpp-a")
        self.assertEqual(sent["context"]["bppUri"], "http://bpp-a")

    def test_the_chosen_provider_is_remembered_for_later_actions(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        self._answer_discover(tid, "bpp-a")
        self._answer_discover(tid, "bpp-b")
        self._select(tid, context={"bppId": "bpp-b"})

        response = self.client.post(
            reverse("beckn-bap-action", kwargs={"action": "confirm"}),
            {"transactionId": tid, "message": {"contract": {}}},
            format="json",
        )

        self.assertEqual(response.status_code, 202)
        sent = txn_store.get_action(tid, "CONFIRM")
        self.assertEqual(sent["context"]["bppId"], "bpp-b")

    def test_callback_posted_to_the_action_path_is_applied(self):
        """A counterparty advertising the plain BAP url still gets through."""
        tid = txn_store.create_transaction("consultation")["transactionId"]
        self.client.force_authenticate(None)

        response = self.client.post(
            reverse("beckn-bap-action-callback", kwargs={"action": "on_discover"}),
            {
                "context": {
                    "action": "on_discover",
                    "transactionId": tid,
                    "bppId": "bpp-a",
                    "bppUri": "http://bpp-a",
                },
                "message": {"catalogs": []},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        record = txn_store.get_transaction(tid)
        self.assertEqual(record["status"], "ON_DISCOVER")
        self.assertEqual(record["routingByBpp"]["bpp-a"]["bppUri"], "http://bpp-a")


@override_settings(BECKN_SYSTEM_USERNAME="beckn_sys")
class OutboundConfirmTests(CareAPITestBase):
    def test_confirm_carries_the_patients_abha_but_not_its_care_id(self):
        patient = self.create_patient(
            name="Meena Joshi", gender="female", date_of_birth=datetime.date(1990, 4, 2)
        )
        config = PatientIdentifierConfig.objects.create(
            facility=None,
            status="active",
            config={
                "use": "official",
                "system": ABHA_IDENTIFIER_SYSTEM,
                "display": "ABHA Number",
            },
        )
        PatientIdentifier.objects.create(
            patient=patient, config=config, value="91-1111-2222-3333"
        )

        confirm = get_adapter("consultation").build_confirm(
            "t1", {}, {}, {"patient": str(patient.external_id)}
        )

        attributes = confirm["message"]["contract"]["participants"][0]
        self.assertEqual(attributes["descriptor"]["name"], "Meena Joshi")
        self.assertEqual(
            attributes["participantAttributes"]["healthIds"],
            [{"system": "ABHA", "value": "91-1111-2222-3333"}],
        )
        self.assertEqual(attributes["participantAttributes"]["gender"], "FEMALE")
        self.assertEqual(
            attributes["participantAttributes"]["dateOfBirth"], "1990-04-02"
        )
        # The Care patient id means nothing off this instance and is not sent.
        self.assertNotIn(str(patient.external_id), json.dumps(confirm))


@override_settings(BECKN_SYSTEM_USERNAME="beckn_sys")
class InboundCallbackSideEffectTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user(username="beckn_sys")
        self.facility = self.create_facility(user=self.user)

    def _referral(self, coordination_id, status=StatusChoices.approved.value):
        return ResourceRequest.objects.create(
            origin_facility=self.facility,
            title="ref",
            status=status,
            category=CategoryChoices.other.value,
            created_by=self.user,
            updated_by=self.user,
            extensions={"beckn": {"coordinationId": coordination_id}},
        )

    def _post(self, action, transaction_id, contract):
        return self.client.post(
            reverse("beckn-bap-receiver-action", kwargs={"action": action}),
            {
                "context": {"action": action, "transactionId": transaction_id},
                "message": {"contract": contract},
            },
            format="json",
        )

    def test_on_cancel_cancels_the_referral(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        referral = self._referral(tid)

        self._post(
            "on_cancel",
            tid,
            {
                "status": {"code": "CANCELLED"},
                "contractAttributes": {
                    "@type": "hrf:HealthReferral",
                    "coordinationId": tid,
                    "lifecycleState": "CANCELLED",
                },
            },
        )

        referral.refresh_from_db()
        self.assertEqual(referral.status, StatusChoices.cancelled.value)

    def test_on_status_fulfilled_completes_the_referral(self):
        tid = txn_store.create_transaction("consultation")["transactionId"]
        referral = self._referral(tid)

        self._post(
            "on_status",
            tid,
            {
                "status": {"code": "ACTIVE"},
                "contractAttributes": {
                    "@type": "hrf:HealthReferral",
                    "coordinationId": tid,
                    "lifecycleState": "FULFILLED",
                },
            },
        )

        referral.refresh_from_db()
        self.assertEqual(referral.status, StatusChoices.completed.value)

    def test_remote_appointment_is_recorded_on_the_referral_it_fulfils(self):
        tid = txn_store.create_transaction("appointment")["transactionId"]
        referral = self._referral("COORD-A")

        self._post(
            "on_confirm",
            tid,
            {
                "id": "remote-booking-1",
                "status": {"code": "ACTIVE"},
                "contractAttributes": {
                    "@type": "hct:HealthContract",
                    "coordinationRef": "COORD-A",
                },
            },
        )

        referral.refresh_from_db()
        self.assertEqual(referral.status, StatusChoices.transfer_in_progress.value)
        self.assertEqual(
            referral.extensions["beckn"]["appointment"]["id"], "remote-booking-1"
        )
        self.assertEqual(
            txn_store.get_transaction(tid)["resourceRequestId"],
            str(referral.external_id),
        )


class CompleteReferralTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)

    def test_fulfilled_booking_completes_referral(self):
        rr = ResourceRequest.objects.create(
            origin_facility=self.facility,
            title="ref",
            status=StatusChoices.approved.value,
            category=CategoryChoices.other.value,
            created_by=self.user,
            updated_by=self.user,
            extensions={"beckn": {"coordinationId": "COORD-1"}},
        )
        booking = SimpleNamespace(id=1, meta={"beckn": {"coordinationRef": "COORD-1"}})
        complete_referral_for_booking(booking)
        rr.refresh_from_db()
        self.assertEqual(rr.status, StatusChoices.completed.value)

    def test_no_coordination_ref_is_noop(self):
        rr = ResourceRequest.objects.create(
            origin_facility=self.facility,
            title="ref",
            status=StatusChoices.approved.value,
            category=CategoryChoices.other.value,
            created_by=self.user,
            updated_by=self.user,
            extensions={"beckn": {"coordinationId": "COORD-2"}},
        )
        booking = SimpleNamespace(id=2, meta={"beckn": {}})
        complete_referral_for_booking(booking)
        rr.refresh_from_db()
        self.assertEqual(rr.status, StatusChoices.approved.value)
