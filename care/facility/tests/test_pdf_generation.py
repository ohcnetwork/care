import hashlib
import subprocess
import tempfile
from datetime import date
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from care.facility.models import (
    ConditionVerificationStatus,
    ICD11Diagnosis,
    PrescriptionDosageType,
    PrescriptionType,
)
from care.facility.utils.reports import discharge_summary
from care.facility.utils.reports.discharge_summary import compile_typ
from care.utils.tests.test_utils import TestUtils


def compare_images(image1_path: Path, image2_path: Path) -> bool:
    with Image.open(image1_path) as img1, Image.open(image2_path) as img2:
        if img1.mode != img2.mode or img1.size != img2.size:
            return False

        img1_hash = hashlib.sha256(img1.tobytes()).hexdigest()
        img2_hash = hashlib.sha256(img2.tobytes()).hexdigest()

    return img1_hash == img2_hash


def test_compile_typ(data) -> bool:
    logo_path = (
        Path(settings.BASE_DIR) / "staticfiles" / "images" / "logos" / "black-logo.svg"
    )
    data["logo_path"] = str(logo_path)
    content = render_to_string(
        "reports/patient_discharge_summary_pdf_template.typ", context=data
    )

    sample_files_dir: Path = (
        settings.BASE_DIR / "care" / "facility" / "tests" / "sample_reports"
    )

    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "typst",
            "compile",
            "-",
            sample_files_dir / "test_output{n}.png",
            "--format",
            "png",
        ],
        input=content.encode("utf-8"),
        capture_output=True,
        check=True,
        cwd="/",
    )

    sample_files = sorted(sample_files_dir.glob("sample*.png"))
    test_generated_files = sorted(sample_files_dir.glob("test_output*.png"))

    result = all(
        compare_images(sample_image, test_output_image)
        for sample_image, test_output_image in zip(
            sample_files, test_generated_files, strict=True
        )
    )

    for file in test_generated_files:
        file.unlink()

    return result


class TestTypstInstallation(TestCase):
    def test_typst_installed(self):
        try:
            subprocess.run(["typst", "--version"], check=True, capture_output=True)  # noqa: S603, S607
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
            cls.super_user, cls.district, cls.local_body, name="_Sample_Facility"
        )
        cls.user = cls.create_user("staff1", cls.district, home_facility=cls.facility)
        cls.treating_physician = cls.create_user(
            "test Doctor",
            cls.district,
            home_facility=cls.facility,
            first_name="Doctor",
            last_name="Tester",
            user_type=15,
        )
        cls.patient = cls.create_patient(
            cls.district, cls.facility, local_body=cls.local_body
        )
        cls.consultation = cls.create_consultation(
            cls.patient,
            cls.facility,
            patient_no="123456",
            doctor=cls.treating_physician,
            height=178,
            weight=80,
            suggestion="A",
        )
        cls.create_patient_sample(cls.patient, cls.consultation, cls.facility, cls.user)
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
        cls.create_prescription(
            cls.consultation, cls.user, dosage_type=PrescriptionDosageType.TITRATED
        )
        cls.create_prescription(
            cls.consultation, cls.user, dosage_type=PrescriptionDosageType.PRN
        )
        cls.create_prescription(
            cls.consultation, cls.user, prescription_type=PrescriptionType.DISCHARGE
        )
        cls.create_prescription(
            cls.consultation,
            cls.user,
            prescription_type=PrescriptionType.DISCHARGE,
            dosage_type=PrescriptionDosageType.TITRATED,
        )
        cls.create_prescription(
            cls.consultation,
            cls.user,
            prescription_type=PrescriptionType.DISCHARGE,
            dosage_type=PrescriptionDosageType.PRN,
        )
        cls.create_consultation_diagnosis(
            cls.consultation,
            ICD11Diagnosis.objects.filter(
                label="SG31 Conception vessel pattern (TM1)"
            ).first(),
            verification_status=ConditionVerificationStatus.CONFIRMED,
        )
        cls.create_consultation_diagnosis(
            cls.consultation,
            ICD11Diagnosis.objects.filter(
                label="SG2B Liver meridian pattern (TM1)"
            ).first(),
            verification_status=ConditionVerificationStatus.DIFFERENTIAL,
        )
        cls.create_consultation_diagnosis(
            cls.consultation,
            ICD11Diagnosis.objects.filter(
                label="SG29 Triple energizer meridian pattern (TM1)"
            ).first(),
            verification_status=ConditionVerificationStatus.PROVISIONAL,
        )
        cls.create_consultation_diagnosis(
            cls.consultation,
            ICD11Diagnosis.objects.filter(
                label="SG60 Early yang stage pattern (TM1)"
            ).first(),
            verification_status=ConditionVerificationStatus.UNCONFIRMED,
        )

    def setUp(self) -> None:
        self.client = APIClient()

    def test_pdf_generation_success(self):
        test_data = {"consultation": self.consultation}

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as file:
            compile_typ(file.name, test_data)

        self.assertTrue(Path(file.name).exists())
        self.assertGreater(Path(file.name).stat().st_size, 0)

    def test_pdf_generation(self):
        data = discharge_summary.get_discharge_summary_data(self.consultation)
        data["date"] = date(2020, 1, 1)

        # This sorting is test's specific and done in order to keep the values in order
        self.assertTrue(test_compile_typ(data))
