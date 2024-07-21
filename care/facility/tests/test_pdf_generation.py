import os
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from care.facility.utils.reports import discharge_summary
from care.facility.utils.reports.discharge_summary import compile_typ
from care.utils.tests.test_utils import TestUtils


def compare_pngs(png_path1, png_path2):
    with Image.open(png_path1) as img1, Image.open(png_path2) as img2:
        if img1.mode != img2.mode:
            print("PNG files differ in mode.")
            return False

        if img1.size != img2.size:
            print("PNG files differ in size.")
            return False

        img1_data = list(img1.getdata())
        img2_data = list(img2.getdata())

    if img1_data == img2_data:
        return True
    else:
        return False


def test_compile_typ(data):
    sample_file_path = os.path.join(
        os.getcwd(), "care", "facility", "utils", "reports", "sample{n}.png"
    )
    test_output_file_path = os.path.join(
        os.getcwd(), "care", "facility", "utils", "reports", "test_output{n}.png"
    )
    try:
        logo_path = (
            Path(settings.BASE_DIR)
            / "staticfiles"
            / "images"
            / "logos"
            / "black-logo.svg"
        )
        data["logo_path"] = str(logo_path)
        content = render_to_string(
            "reports/patient_discharge_summary_pdf_template.typ", context=data
        )
        subprocess.run(
            ["typst", "compile", "-", test_output_file_path, "--format", "png"],
            input=content.encode("utf-8"),
            capture_output=True,
            check=True,
            cwd="/",
        )
        for i in range(1, 4):
            current_sample_file_path = sample_file_path
            current_sample_file_path = str(current_sample_file_path).replace(
                "{n}", str(i)
            )

            current_test_output_file_path = test_output_file_path
            current_test_output_file_path = str(current_test_output_file_path).replace(
                "{n}", str(i)
            )

            if not compare_pngs(
                Path(current_sample_file_path), Path(current_test_output_file_path)
            ):
                return False

        return True
    except subprocess.CalledProcessError:
        return False
    except Exception:
        return False
    finally:
        count = 1
        while True:
            current_test_output_file_path = test_output_file_path
            current_test_output_file_path = current_test_output_file_path.replace(
                "{n}", str(count)
            )
            if Path(current_test_output_file_path).exists():
                os.remove(Path(current_test_output_file_path))
            else:
                break
            count += 1


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
        cls.state = cls.create_state(name="sample_state")
        cls.district = cls.create_district(cls.state, name="sample_district")
        cls.local_body = cls.create_local_body(cls.district, name="sample_local_body")
        cls.super_user = cls.create_super_user("su", cls.district)
        cls.facility = cls.create_facility(
            cls.super_user, cls.district, cls.local_body, name="Sample Facility"
        )
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.consultation = cls.create_consultation(
            cls.patient, cls.facility, patient_no="123456"
        )
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
        data = discharge_summary.get_discharge_summary_data(self.consultation)
        data["date"] = date(2020, 1, 1)
        self.assertTrue(test_compile_typ(data))
