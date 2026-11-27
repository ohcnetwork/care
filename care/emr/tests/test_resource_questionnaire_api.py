from datetime import timedelta
from uuid import uuid4

from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from model_bakery import baker

from care.emr.models.device import Device
from care.emr.models.facility_resource import (
    FacilityResourceObservation,
    FacilityResourceQuestionnaireResponse,
)
from care.emr.models.location import FacilityLocation
from care.emr.models.questionnaire import Questionnaire
from care.security.permissions.questionnaire import QuestionnairePermissions
from care.utils.tests.base import CareAPITestBase


class ResourceQuestionnaireAPITests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.facility.default_internal_organization
        self.question = {
            "id": str(uuid4()),
            "link_id": "temperature",
            "text": "Temperature",
            "type": "decimal",
            "required": True,
            "code": {
                "system": "http://loinc.org",
                "code": "8310-5",
                "display": "Body temperature",
            },
        }
        self.questionnaire = self.create_questionnaire()
        self.client.force_authenticate(self.user)

    def create_questionnaire(self, **kwargs):
        return baker.make(
            Questionnaire,
            **(
                {
                    "title": "Resource assessment",
                    "auth_context": "facility",
                    "facility": self.facility,
                    "subject_type": "facility",
                    "status": "active",
                    "questions": [self.question],
                }
                | kwargs
            ),
        )

    def submit(self, resource=None, questionnaire=None, value="37.5"):
        questionnaire = questionnaire or self.questionnaire
        resource = resource or self.facility
        return self.client.post(
            reverse(
                "questionnaire-submit-resource",
                kwargs={"external_id": questionnaire.external_id},
            ),
            {
                "resource_id": str(resource.external_id),
                "results": [
                    {"question_id": self.question["id"], "values": [{"value": value}]}
                ],
            },
            format="json",
        )

    def subject_params(self, resource=None, subject_type="facility"):
        return {
            "subject_id": str((resource or self.facility).external_id),
            "subject_type": subject_type,
        }

    def response_url(self, response):
        return reverse(
            "resource-responses-detail", kwargs={"external_id": response.external_id}
        )

    def create_response(self, **kwargs):
        return baker.make(
            FacilityResourceQuestionnaireResponse,
            **(
                {
                    "facility": self.facility,
                    "questionnaire": self.questionnaire,
                    "subject_type": "facility",
                    "subject_id": self.facility.external_id,
                    "created_by": self.user,
                    "updated_by": self.user,
                    "structured_response_type": "",
                }
                | kwargs
            ),
        )

    def test_submission_creates_responses_and_observations_for_each_resource_type(self):
        location = baker.make(FacilityLocation, facility=self.facility)
        device = baker.make(Device, facility=self.facility)
        for subject_type, resource in (
            ("facility", self.facility),
            ("location", location),
            ("device", device),
        ):
            with self.subTest(subject_type=subject_type):
                questionnaire = self.create_questionnaire(subject_type=subject_type)
                response = self.submit(resource, questionnaire)
                self.assertEqual(response.status_code, 200, response.data)
                stored = FacilityResourceQuestionnaireResponse.objects.get(
                    external_id=response.data["id"]
                )
                self.assertEqual(stored.subject_type, subject_type)
                self.assertEqual(stored.subject_id, resource.external_id)
                self.assertEqual(stored.facility, self.facility)
                self.assertEqual(stored.cleaned_response, {"temperature": 37.5})
                self.assertEqual(stored.revision, questionnaire.internal_revision)
                observation = FacilityResourceObservation.objects.get(
                    questionnaire_response=stored
                )
                self.assertEqual(observation.subject_id, resource.external_id)
                self.assertEqual(observation.subject_type, subject_type)
                self.assertEqual(observation.value["value"], "37.5")

    def test_submission_rejects_a_resource_from_another_facility(self):
        other_facility = self.create_facility(user=self.user)
        response = self.submit(other_facility)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(FacilityResourceQuestionnaireResponse.objects.exists())
        self.assertFalse(FacilityResourceObservation.objects.exists())

    def test_invalid_answers_do_not_create_responses_or_observations(self):
        response = self.submit(value="invalid")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(FacilityResourceQuestionnaireResponse.objects.exists())
        self.assertFalse(FacilityResourceObservation.objects.exists())

    def test_submission_requires_resource_permission(self):
        self.client.force_authenticate(self.create_user())
        response = self.submit()
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(FacilityResourceQuestionnaireResponse.objects.exists())

    def test_read_permission_does_not_grant_submission_for_any_resource_type(self):
        reader = self.create_user()
        role = self.create_role_with_permissions(
            [QuestionnairePermissions.can_view_resource_responses.name]
        )
        self.attach_role_facility_organization_user(self.organization, reader, role)
        resources = (
            ("facility", self.facility),
            (
                "location",
                baker.make(
                    FacilityLocation,
                    facility=self.facility,
                ),
            ),
            (
                "device",
                baker.make(
                    Device,
                    facility=self.facility,
                ),
            ),
        )
        self.client.force_authenticate(reader)
        for subject_type, resource in resources:
            with self.subTest(subject_type=subject_type):
                questionnaire = self.create_questionnaire(subject_type=subject_type)
                stored = self.create_response(
                    questionnaire=questionnaire,
                    subject_type=subject_type,
                    subject_id=resource.external_id,
                )
                listed = self.client.get(
                    reverse("resource-responses-list"),
                    self.subject_params(resource, subject_type),
                )
                self.assertEqual(listed.status_code, 200, listed.data)
                self.assertEqual(
                    [item["id"] for item in listed.data["results"]],
                    [str(stored.external_id)],
                )
                denied = self.submit(resource, questionnaire)
                self.assertEqual(denied.status_code, 403, denied.data)

    def test_submission_permission_allows_recent_correction_and_does_not_grant_read(
        self,
    ):
        submitter = self.create_user()
        role = self.create_role_with_permissions(
            [QuestionnairePermissions.can_submit_questionnaire.name]
        )
        self.attach_role_facility_organization_user(self.organization, submitter, role)
        self.client.force_authenticate(submitter)
        submitted = self.submit()
        self.assertEqual(submitted.status_code, 200, submitted.data)
        stored = FacilityResourceQuestionnaireResponse.objects.get(
            external_id=submitted.data["id"]
        )
        updated = self.client.put(
            self.response_url(stored), {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        stored.refresh_from_db()
        self.assertEqual(stored.status, "entered_in_error")
        self.assertEqual(stored.updated_by, submitter)
        listed = self.client.get(
            reverse("resource-responses-list"), self.subject_params()
        )
        self.assertEqual(listed.status_code, 403, listed.data)

    def test_response_and_observation_lists_require_subject_filters(self):
        for route in ("resource-responses-list", "resource-observation-list"):
            for params in (
                {},
                {"subject_id": str(self.facility.external_id)},
                {"subject_type": "facility"},
            ):
                with self.subTest(route=route, params=params):
                    response = self.client.get(reverse(route), params)
                    self.assertEqual(response.status_code, 400, response.data)

    def test_subject_lookup_rejects_unknown_resource_types_and_missing_resources(self):
        for route in ("resource-responses-list", "resource-observation-list"):
            for params, status in (
                (self.subject_params(subject_type="patient"), 400),
                ({"subject_type": "facility", "subject_id": str(uuid4())}, 404),
            ):
                with self.subTest(route=route, params=params):
                    response = self.client.get(reverse(route), params)
                    self.assertEqual(response.status_code, status, response.data)

    def test_subject_filter_prevents_reading_another_resource_response(self):
        wanted = self.create_response()
        other = self.create_response(subject_id=uuid4())
        response = self.client.get(
            reverse("resource-responses-list"), self.subject_params()
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            [item["id"] for item in response.data["results"]], [str(wanted.external_id)]
        )
        detail = self.client.get(self.response_url(other), self.subject_params())
        self.assertEqual(detail.status_code, 404, detail.data)

    def test_response_filters_select_questionnaire_status_and_creator(self):
        wanted = self.create_response()
        self.create_response(questionnaire=self.create_questionnaire())
        self.create_response(status="entered_in_error")
        other_user = self.create_user()
        self.create_response(created_by=other_user)
        for questionnaire_filter in (
            {"questionnaire": str(self.questionnaire.external_id)},
            {"questionnaire_slug": self.questionnaire.slug},
            {"questionnaire_slugs": self.questionnaire.slug},
        ):
            params = (
                self.subject_params()
                | questionnaire_filter
                | {"status": "completed", "created_by": str(self.user.external_id)}
            )
            with self.subTest(params=params):
                response = self.client.get(reverse("resource-responses-list"), params)
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    [str(wanted.external_id)],
                )

    def test_read_permission_is_required_for_response_and_observation_lists(self):
        self.create_response()
        self.client.force_authenticate(self.create_user())
        for route in ("resource-responses-list", "resource-observation-list"):
            with self.subTest(route=route):
                response = self.client.get(reverse(route), self.subject_params())
                self.assertEqual(response.status_code, 403, response.data)

    def test_marking_response_in_error_updates_only_its_observations(self):
        submitted = self.submit()
        self.assertEqual(submitted.status_code, 200, submitted.data)
        stored = FacilityResourceQuestionnaireResponse.objects.get(
            external_id=submitted.data["id"]
        )
        other_submitted = self.submit(value="38.0")
        self.assertEqual(other_submitted.status_code, 200, other_submitted.data)
        updated = self.client.put(
            self.response_url(stored), {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        stored.refresh_from_db()
        self.assertEqual(stored.status, "entered_in_error")
        self.assertEqual(
            FacilityResourceObservation.objects.get(
                questionnaire_response=stored
            ).status,
            "entered_in_error",
        )
        self.assertEqual(
            FacilityResourceObservation.objects.exclude(questionnaire_response=stored)
            .get()
            .status,
            "final",
        )

    def test_an_errored_response_cannot_be_edited_even_by_a_superuser(self):
        response = self.create_response(status="entered_in_error")
        updated = self.client.put(
            self.response_url(response), {"status": "completed"}, format="json"
        )
        self.assertEqual(updated.status_code, 403, updated.data)
        response.refresh_from_db()
        self.assertEqual(response.status, "entered_in_error")

    def test_regular_users_cannot_edit_an_expired_response(self):
        response = self.create_response()
        FacilityResourceQuestionnaireResponse.objects.filter(pk=response.pk).update(
            created_date=timezone.now()
            - timedelta(minutes=settings.QUESTIONNAIRE_ERRORED_TIME_LIMIT_MINUTES + 1)
        )
        self.client.force_authenticate(self.create_user())
        updated = self.client.put(
            self.response_url(response), {"status": "entered_in_error"}, format="json"
        )
        self.assertEqual(updated.status_code, 403, updated.data)

    def test_response_rendering_uses_the_submitted_revision(self):
        old_question = self.question | {"text": "Original temperature label"}
        past = self.create_questionnaire(
            latest_revision=self.questionnaire,
            internal_revision=1,
            questions=[old_question],
        )
        self.questionnaire.internal_revision = 2
        self.questionnaire.save(update_fields=["internal_revision"])
        answer = {"question_id": self.question["id"], "values": [{"value": "37.5"}]}
        response = self.create_response(
            revision=1, responses=[answer, {"question_id": str(uuid4())}]
        )
        self.assertEqual(response.resolved_questionnaire, past)
        self.assertEqual(
            response.render_responses(), [{"answer": answer, "question": old_question}]
        )

    def test_observation_code_filters_and_analysis_are_scoped_to_the_subject(self):
        for value in ("37.5", "38.0"):
            submitted = self.submit(value=value)
            self.assertEqual(submitted.status_code, 200, submitted.data)
        other_facility = self.create_facility(user=self.user)
        other_form = self.create_questionnaire(facility=other_facility)
        other = self.submit(other_facility, other_form, value="40.0")
        self.assertEqual(other.status_code, 200, other.data)
        response = self.client.get(
            reverse("resource-observation-list"),
            self.subject_params() | {"codes": "8310-5"},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 2)
        missing = self.client.get(
            reverse("resource-observation-list"),
            self.subject_params() | {"codes": "missing"},
        )
        self.assertEqual(missing.status_code, 200, missing.data)
        self.assertEqual(missing.data["count"], 0)
        analysed = self.client.post(
            reverse("resource-observation-analyse")
            + f"?subject_id={self.facility.external_id}&subject_type=facility",
            {"codes": [self.question["code"]], "page_size": 1},
            format="json",
        )
        self.assertEqual(analysed.status_code, 200, analysed.data)
        result = analysed.data["results"][0]
        self.assertEqual(result["code"]["code"], "8310-5")
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(
            str(result["results"][0]["subject_id"]), str(self.facility.external_id)
        )
        self.assertEqual(result["results"][0]["value"]["value"], "38.0")

    def test_analysis_validates_code_count_and_page_size(self):
        url = (
            reverse("resource-observation-analyse")
            + f"?subject_id={self.facility.external_id}&subject_type=facility"
        )
        for payload in (
            {"codes": []},
            {"codes": [self.question["code"]], "page_size": 31},
        ):
            with self.subTest(payload=payload):
                response = self.client.post(url, payload, format="json")
                self.assertEqual(response.status_code, 400, response.data)
