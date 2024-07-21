import os
import subprocess
import tempfile

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from care.facility.utils.reports import discharge_summary
from care.facility.utils.reports.discharge_summary import compile_typ
from care.utils.tests.test_utils import TestUtils


class TestTypstInstallation(TestCase):
    def test_typst_installed(self):
        try:
            subprocess.run(["typst", "--version"], check=True)
            typst_installed = True
        except subprocess.CalledProcessError:
            typst_installed = False

        self.assertTrue(typst_installed, "Typst is not installed or not accessible")


class TestGenerateDischargeSummaryPDF(TestCase, TestUtils):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.state = cls.create_state()
        cls.district = cls.create_district(cls.state)
        cls.local_body = cls.create_local_body(cls.district)
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(cls.super_user, cls.district, cls.local_body)
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.consultation = cls.create_consultation(cls.patient, cls.facility)
        cls.create_patient_sample(cls.patient, cls.consultation, cls.facility, cls.user)
        cls.create_policy(patient=cls.patient, user=cls.user)
        cls.create_encounter_symptom(cls.consultation, cls.user)
        cls.patient_investigation_group = cls.create_patient_investigation_group()
        cls.patient_investigation = cls.create_patient_investigation(
            cls.patient_investigation_group
        )
        cls.patient_investigation_session = cls.create_patient_investigation_session(
            cls.user
        )
        cls.create_investigation_value(
            cls.patient_investigation,
            cls.consultation,
            cls.patient_investigation_session,
            cls.patient_investigation_group,
        )
        cls.create_disease(cls.patient)
        cls.create_prescription(cls.consultation, cls.user)
        # Todo : prn and prn prescriptions
        # TODO: create few values with titration for prescription
        # Todo: Create diagnoses

    def setUp(self) -> None:
        self.client = APIClient()

    def test_pdf_generation_success(self):
        test_data = {"consultation": self.consultation}

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as file:
            compile_typ(file.name, test_data)

        self.assertTrue(os.path.exists(file.name))
        self.assertGreater(os.path.getsize(file.name), 0)

    def test_pdf_generation(self):
        # This function to generate the sample report , tests are yet to be written
        output_file_path = os.path.join(os.getcwd(), "output.pdf")
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        data = discharge_summary.get_discharge_summary_data(self.consultation)
        data["date"] = timezone.now()

        compile_typ(output_file_path, data)

        # Todo: Test is yet to be written
