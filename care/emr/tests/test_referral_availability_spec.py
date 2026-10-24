from django.test import TestCase
from model_bakery import baker
from rest_framework.exceptions import ValidationError

from care.emr.models.organization import FacilityOrganization
from care.emr.models.questionnaire import Questionnaire
from care.emr.models.referral import ReferralAvailability
from care.emr.resources.questionnaire.spec import SubjectType
from care.emr.resources.referral.availability import (
    ReferralAvailabilityCreateSpec,
    resolve_questionnaires,
)
from care.facility.models.facility import Facility
from care.users.models import User


class ReferralAvailabilityCreationSpecTests(TestCase):
    def setUp(self):
        self.user = baker.make(User)
        self.facility = baker.make(Facility, created_by=self.user)
        self.organization = baker.make(FacilityOrganization, facility=self.facility)
        self.payload = {
            "entity_type": "internal_organization",
            "internal_organization": str(self.organization.external_id),
            "name": "Department consultation",
            "status": "active",
            "referral_type": "consultation",
        }

    def test_internal_organization_facility_is_automatically_set_and_persisted(self):
        for facility_data in (
            {},
            {"facility": None},
            {"facility": str(self.facility.external_id)},
        ):
            with self.subTest(facility_data=facility_data):
                spec = ReferralAvailabilityCreateSpec.model_validate(
                    {**self.payload, **facility_data}
                )
                availability = spec.de_serialize()
                self.assertEqual(availability.facility_id, self.facility.id)
                self.assertEqual(
                    availability.internal_organization_id, self.organization.id
                )
                availability.save()
                availability.refresh_from_db()
                self.assertEqual(availability.facility_id, self.facility.id)
                self.assertEqual(
                    availability.internal_organization_id, self.organization.id
                )

    def test_internal_organization_rejects_a_different_facility(self):
        other_facility = baker.make(Facility, created_by=self.user)
        spec = ReferralAvailabilityCreateSpec.model_validate(
            {**self.payload, "facility": str(other_facility.external_id)}
        )
        with self.assertRaisesMessage(
            ValidationError, "Facility must match the internal organization's facility"
        ):
            spec.de_serialize()
        self.assertFalse(ReferralAvailability.objects.exists())


class ReferralAvailabilityQuestionnaireSpecTests(TestCase):
    def test_patient_and_encounter_questionnaires_are_resolved(self):
        questionnaires = [
            baker.make(Questionnaire, status="active", subject_type=subject.value)
            for subject in (SubjectType.patient, SubjectType.encounter)
        ]

        resolved = resolve_questionnaires(
            [questionnaire.external_id for questionnaire in questionnaires]
        )

        self.assertCountEqual(resolved, questionnaires)

    def test_other_subjects_are_rejected_including_mixed_requests(self):
        patient_questionnaire = baker.make(
            Questionnaire, status="active", subject_type=SubjectType.patient.value
        )
        for subject in (SubjectType.location, SubjectType.device, SubjectType.facility):
            questionnaire = baker.make(
                Questionnaire, status="active", subject_type=subject.value
            )
            for identifiers in (
                [questionnaire.external_id],
                [patient_questionnaire.external_id, questionnaire.external_id],
            ):
                with (
                    self.subTest(subject=subject, identifiers=identifiers),
                    self.assertRaises(ValidationError),
                ):
                    resolve_questionnaires(identifiers)
