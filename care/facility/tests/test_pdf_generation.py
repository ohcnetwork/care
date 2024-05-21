import os
import subprocess
import tempfile

from django.test import TestCase
from rest_framework.test import APIClient

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

    def setUp(self) -> None:
        self.client = APIClient()

    def test_pdf_generation_success(self):
        test_data = {"consultation": self.consultation}

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as file:
            compile_typ(file.name, test_data)

            self.assertTrue(os.path.exists(file.name))
            self.assertGreater(os.path.getsize(file.name), 0)
