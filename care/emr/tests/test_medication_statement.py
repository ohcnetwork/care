from datetime import UTC, datetime, timedelta

from django.urls import reverse
from model_bakery import baker
from pydantic import ValidationError

from care.emr.resources.medication.statement.spec import MedicationStatementSpec
from care.emr.resources.common.period import Period
from care.utils.tests.base import CareAPITestBase


class TestMedicationStatementSpec(CareAPITestBase):
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
        self.valid_code = {
            "display": "Test Value",
            "system": "http://test_system.care/test",
            "code": "123",
        }

    def test_validate_effective_period_valid_dates(self):
        """Test that valid date range passes validation"""
        start_date = datetime.now(UTC)
        end_date = start_date + timedelta(days=7)

        period = Period(start=start_date, end=end_date)

        data = {
            "status": "active",
            "medication": self.valid_code,
            "encounter": self.encounter.external_id,
            "effective_period": period,
        }
        MedicationStatementSpec(**data)

    def test_validate_effective_period_invalid_dates(self):
        """Test that invalid date range (end before start) raises validation error"""
        start_date = datetime.now(UTC)
        end_date = start_date - timedelta(days=7)  # End date before start date

        period = Period(start=start_date, end=end_date)

        data = {
            "status": "active",
            "medication": self.valid_code,
            "encounter": self.encounter.external_id,
            "effective_period": period,
        }

        with self.assertRaises(ValidationError) as context:
            MedicationStatementSpec(**data)

        self.assertIn("Start date must be before end date", str(context.exception))
