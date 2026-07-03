"""Tests for the Care-as-BAP Beckn orchestration (Redis-backed discover/select/
confirm) and the appointment -> referral completion hook."""

from types import SimpleNamespace

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from care.beckn.services import txn_store
from care.beckn.services.flows import FlowError, get_adapter
from care.beckn.tasks import complete_referral_for_booking
from care.emr.models.resource_request import ResourceRequest
from care.emr.resources.resource_request.spec import CategoryChoices, StatusChoices
from care.utils.tests.base import CareAPITestBase


class TxnStoreTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        cache.clear()

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
        self.assertEqual(rec["responses"]["ON_DISCOVER"], {"y": 2})

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
        cache.clear()
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
