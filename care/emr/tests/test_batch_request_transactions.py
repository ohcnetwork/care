from django.db import connections
from django.test import TransactionTestCase, override_settings
from django.urls import path, reverse
from model_bakery import baker
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.test import APIClient
from rest_framework.views import APIView

from care.emr.api.viewsets.base import emr_exception_handler
from care.emr.api.viewsets.batch_request import BatchRequestView
from care.emr.models.account import Account
from care.utils.lock import ObjectLocked


class BatchTransactionStepView(APIView):
    authentication_classes = ()
    permission_classes = ()
    calls = []

    def get_exception_handler(self):
        return emr_exception_handler

    def post(self, request):
        self.calls.append(request.data["step"])
        account = Account.objects.get(pk=request.data["account"])
        observed_name = account.name
        if "name" in request.data:
            account.name = request.data["name"]
            account.save(update_fields=["name"])
        failure = request.data.get("failure")
        if failure == "locked":
            raise ObjectLocked
        if failure == "validation":
            raise ValidationError("Invalid step after writing")
        if failure == "unexpected":
            raise RuntimeError("Unexpected batch step failure")
        return Response(
            {"observed_name": observed_name, "name": account.name},
            status=request.data.get("status_code", 200),
        )


urlpatterns = [
    path(
        "batch-transaction-tests/",
        BatchRequestView.as_view({"post": "create"}),
        name="transaction-test-batch",
    ),
    path(
        "batch-transaction-tests/step/",
        BatchTransactionStepView.as_view(),
        name="transaction-test-step",
    ),
]


@override_settings(ROOT_URLCONF=__name__, DEBUG_PROPAGATE_EXCEPTIONS=True)
class BatchRequestTransactionTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        database_settings = connections["default"].settings_dict
        original_atomic_requests = database_settings["ATOMIC_REQUESTS"]
        database_settings["ATOMIC_REQUESTS"] = True
        cls.addClassCleanup(
            database_settings.__setitem__, "ATOMIC_REQUESTS", original_atomic_requests
        )

    def setUp(self):
        self.user = baker.make("users.User", is_superuser=True)
        facility = baker.make("facility.Facility", created_by=self.user)
        patient = baker.make("emr.Patient")
        self.account = baker.make(
            Account,
            facility=facility,
            patient=patient,
            name="Original account",
            status="active",
            billing_status="open",
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        BatchTransactionStepView.calls = []

    def step(self, reference_id, **body):
        return {
            "url": reverse("transaction-test-step"),
            "method": "POST",
            "reference_id": reference_id,
            "body": {"account": self.account.pk, "step": reference_id, **body},
        }

    def batch(self, *steps):
        return self.client.post(
            reverse("transaction-test-batch"),
            {"requests": list(steps)},
            format="json",
        )

    def assert_original_account(self):
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "Original account")

    def test_failed_response_rolls_back_its_writes_before_later_request(self):
        response = self.batch(
            self.step("failed", name="Rejected edit", status_code=400),
            self.step("later", name="Later edit"),
        )

        self.assertEqual(response.status_code, 400, response.data)
        results = response.data["results"]
        self.assertEqual(
            [item["reference_id"] for item in results], ["failed", "later"]
        )
        self.assertEqual([item["status_code"] for item in results], [400, 200])
        self.assertEqual(results[1]["data"]["observed_name"], "Original account")
        self.assertEqual(BatchTransactionStepView.calls, ["failed", "later"])
        self.assert_original_account()

    def test_failed_middle_request_preserves_prior_batch_state_until_full_rollback(
        self,
    ):
        response = self.batch(
            self.step("successful", name="Earlier successful edit"),
            self.step("failed", name="Rejected edit", status_code=400),
            self.step("read"),
        )

        self.assertEqual(response.status_code, 400, response.data)
        results = response.data["results"]
        self.assertEqual([item["status_code"] for item in results], [200, 400, 200])
        self.assertEqual(results[2]["data"]["observed_name"], "Earlier successful edit")
        self.assertEqual(
            BatchTransactionStepView.calls, ["successful", "failed", "read"]
        )
        self.assert_original_account()

    def test_lock_error_does_not_break_later_request_queries(self):
        response = self.batch(
            self.step("locked", name="Rejected edit", failure="locked"),
            self.step("later", name="Later edit"),
        )

        self.assertEqual(response.status_code, 400, response.data)
        results = response.data["results"]
        self.assertEqual([item["status_code"] for item in results], [423, 200])
        self.assertIn("locked", str(results[0]["data"]))
        self.assertEqual(results[1]["data"]["observed_name"], "Original account")
        self.assert_original_account()

    def test_custom_validation_error_rolls_back_before_later_request(self):
        response = self.batch(
            self.step("invalid", name="Rejected edit", failure="validation"),
            self.step("later"),
        )

        self.assertEqual(response.status_code, 400, response.data)
        results = response.data["results"]
        self.assertEqual([item["status_code"] for item in results], [400, 200])
        self.assertEqual(results[1]["data"]["observed_name"], "Original account")
        self.assert_original_account()

    def assert_server_error_stops_batch(self, failed_step):
        response = self.batch(
            self.step("successful", name="Earlier successful edit"),
            failed_step,
            self.step("never-executed", name="Must never be saved"),
        )

        self.assertEqual(response.status_code, 500, response.data)
        results = response.data["results"]
        self.assertEqual(
            [item["reference_id"] for item in results], ["successful", "server-error"]
        )
        self.assertEqual([item["status_code"] for item in results], [200, 500])
        self.assertNotIn("data", results[1])
        self.assertEqual(BatchTransactionStepView.calls, ["successful", "server-error"])
        self.assert_original_account()

    def test_server_error_response_stops_later_requests_and_rolls_back_batch(self):
        self.assert_server_error_stops_batch(
            self.step("server-error", name="Rejected edit", status_code=500)
        )

    def test_unhandled_exception_stops_later_requests_and_rolls_back_batch(self):
        with self.assertLogs("care.emr.utils.batch_requests", level="ERROR"):
            self.assert_server_error_stops_batch(
                self.step("server-error", name="Rejected edit", failure="unexpected")
            )

    def test_successful_batch_commits_all_edits_in_order(self):
        response = self.batch(
            self.step("first", name="First edit"),
            self.step("second", name="Final edit"),
        )

        self.assertEqual(response.status_code, 200, response.data)
        results = response.data["results"]
        self.assertEqual(
            [item["reference_id"] for item in results], ["first", "second"]
        )
        self.assertEqual([item["status_code"] for item in results], [200, 200])
        self.assertEqual(results[1]["data"]["observed_name"], "First edit")
        self.account.refresh_from_db()
        self.assertEqual(self.account.name, "Final edit")
