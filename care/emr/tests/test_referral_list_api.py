import uuid
from unittest.mock import patch

from django.urls import reverse
from model_bakery import baker

from care.emr.models.notes import NoteMessage
from care.emr.models.patient import PatientUser
from care.emr.models.questionnaire import Questionnaire
from care.emr.models.referral import Referral, ReferralAvailability, ReferralResource
from care.security.authorization.referral import ReferralAccess
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.referral import ReferralPermissions
from care.utils.tests.base import CareAPITestBase


class ReferralListAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.publisher = self.create_user()
        self.other_user = self.create_user()
        self.origin = self.create_facility(user=self.publisher)
        self.origin_organization = self.create_facility_organization(
            facility=self.origin,
            parent=self.origin.default_internal_organization,
            org_type="dept",
        )
        self.destination = self.create_facility(user=self.publisher)
        self.department = self.create_facility_organization(
            facility=self.destination,
            parent=self.destination.default_internal_organization,
            org_type="dept",
        )
        self.patient = self.create_patient()
        self.other_patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.origin,
            organization=self.origin_organization,
        )
        self.availability = self.make_availability()
        self.referral = self.make_referral()
        self.client.force_authenticate(user=self.user)

    def make_availability(self, *, entity_type="facility", **kwargs):
        if entity_type == "facility":
            kwargs.setdefault("facility", self.destination)
        return ReferralAvailability.objects.create(
            entity_type=entity_type,
            name="Referral service",
            status="active",
            is_public=True,
            referral_type="consultation",
            created_by=self.publisher,
            **kwargs,
        )

    def make_referral(
        self, *, availability=None, encounter=None, patient=None, **kwargs
    ):
        return Referral.objects.create(
            availability=availability or self.availability,
            encounter=encounter,
            patient=patient or (encounter.patient if encounter else self.patient),
            title="Referral request",
            created_by=self.publisher,
            **kwargs,
        )

    def grant(self, organization, *, internal=True, permissions=None, user=None):
        role = self.create_role_with_permissions(
            permissions=permissions or [ReferralPermissions.can_read_referral.name]
        )
        attach = (
            self.attach_role_facility_organization_user
            if internal
            else self.attach_role_organization_user
        )
        return attach(organization, user or self.user, role)

    def grant_origin(self, **kwargs):
        return self.grant(self.origin_organization, **kwargs)

    def grant_destination(self, **kwargs):
        return self.grant(self.destination.default_internal_organization, **kwargs)

    def grant_patient(self):
        role = self.create_role_with_permissions(
            permissions=[ReferralPermissions.can_read_referral.name]
        )
        return PatientUser.objects.create(
            patient=self.patient, user=self.user, role=role
        )

    def entity_scope(self, *, entity_type="facility", entity=None):
        return {
            "entity_type": entity_type,
            "entity_id": str((entity or self.destination).external_id),
        }

    def assert_list(self, params, expected, *, url=None):
        response = self.client.get(url or reverse("referral-list"), params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], len(expected))
        self.assertCountEqual(
            [item["id"] for item in response.data["results"]],
            [str(referral.external_id) for referral in expected],
        )
        return response

    def assign(self, referral, *users):
        referral.assignees = [
            {
                "user_id": user.id,
                "role": {"system": "http://snomed.info/sct", "code": "doctor"},
            }
            for user in users
        ]
        referral.save(update_fields=["assignees"])

    def test_referral_list_requires_a_complete_valid_scope(self):
        for params in (
            {},
            {"status": "pending"},
            {"assigned_to_me": True},
            {"entity_type": "facility"},
            {"entity_id": str(self.destination.external_id)},
            {"entity_type": "facility", "entity_id": "invalid"},
            {"entity_type": "invalid", "entity_id": str(self.destination.external_id)},
            {"entity_type": "external", "entity_id": str(self.destination.external_id)},
            {"patient": "invalid"},
            {"encounter": "invalid"},
            {"entity_type": "facility", "encounter": str(self.encounter.external_id)},
        ):
            with self.subTest(params=params):
                response = self.client.get(reverse("referral-list"), params)
                self.assertEqual(response.status_code, 400, response.data)

    def test_referral_list_missing_scope_objects_return_not_found(self):
        for params in (
            {"entity_type": "facility", "entity_id": str(uuid.uuid4())},
            {"entity_type": "internal_organization", "entity_id": str(uuid.uuid4())},
            {"entity_type": "external_organization", "entity_id": str(uuid.uuid4())},
            {"encounter": str(uuid.uuid4())},
            {"patient": str(uuid.uuid4())},
        ):
            with self.subTest(params=params):
                response = self.client.get(reverse("referral-list"), params)
                self.assertEqual(response.status_code, 404, response.data)

    def test_referral_list_requires_read_permission_for_the_selected_scope(self):
        self.grant_origin(
            permissions=[EncounterPermissions.can_read_encounter_clinical_data.name]
        )
        self.grant_destination(
            permissions=[ReferralPermissions.can_write_referral.name]
        )
        self.assign(self.referral, self.user)
        for params in (
            self.entity_scope(),
            {"encounter": str(self.encounter.external_id)},
            {"patient": str(self.patient.external_id)},
        ):
            with self.subTest(params=params):
                response = self.client.get(reverse("referral-list"), params)
                self.assertEqual(response.status_code, 403, response.data)

    def test_referral_entity_list_requires_root_facility_permission_and_exact_target(
        self,
    ):
        self.grant(self.department)
        denied = self.client.get(reverse("referral-list"), self.entity_scope())
        self.assertEqual(denied.status_code, 403, denied.data)
        self.grant_destination()
        departmental_availability = self.make_availability(
            entity_type="internal_organization",
            internal_organization=self.department,
            facility=self.destination,
        )
        self.make_referral(availability=departmental_availability)
        other_availability = self.make_availability(facility=self.origin)
        self.make_referral(availability=other_availability)
        self.availability.status = "inactive"
        self.availability.save(update_fields=["status"])
        self.assert_list(self.entity_scope(), [self.referral])
        self.assert_list(
            {**self.entity_scope(), "facility": str(self.origin.external_id)}, []
        )

    def test_referral_organization_lists_accept_ancestor_roles_but_only_exact_targets(
        self,
    ):
        external_parent = self.create_organization()
        external_child = self.create_organization(parent=external_parent)
        for entity_type, parent, child, internal in (
            (
                "internal_organization",
                self.destination.default_internal_organization,
                self.department,
                True,
            ),
            ("external_organization", external_parent, external_child, False),
        ):
            with self.subTest(entity_type=entity_type):
                self.grant(parent, internal=internal)
                parent_availability = self.make_availability(
                    entity_type=entity_type, **{entity_type: parent}
                )
                child_availability = self.make_availability(
                    entity_type=entity_type, **{entity_type: child}
                )
                self.make_referral(availability=parent_availability)
                child_referral = self.make_referral(availability=child_availability)
                self.assert_list(
                    self.entity_scope(entity_type=entity_type, entity=child),
                    [child_referral],
                )

    def test_referral_child_organization_role_cannot_list_parent_or_sibling(self):
        for internal in (True, False):
            with self.subTest(internal=internal):
                if internal:

                    def create(**kwargs):
                        return self.create_facility_organization(
                            facility=self.destination, **kwargs
                        )
                else:
                    create = self.create_organization
                parent = create()
                child = create(parent=parent)
                sibling = create(parent=parent)
                self.grant(child, internal=internal)
                entity_type = (
                    "internal_organization" if internal else "external_organization"
                )
                for target in (parent, sibling):
                    response = self.client.get(
                        reverse("referral-list"),
                        self.entity_scope(entity_type=entity_type, entity=target),
                    )
                    self.assertEqual(response.status_code, 403, response.data)

    def test_referral_encounter_list_uses_origin_permission_and_only_that_encounter(
        self,
    ):
        self.grant(self.origin.default_internal_organization)
        encounter_referral = self.make_referral(encounter=self.encounter)
        department_availability = self.make_availability(
            entity_type="internal_organization", internal_organization=self.department
        )
        department_referral = self.make_referral(
            availability=department_availability, encounter=self.encounter
        )
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.origin,
            organization=self.origin_organization,
        )
        self.make_referral(encounter=other_encounter)
        self.assert_list(
            {"encounter": str(self.encounter.external_id)},
            [encounter_referral, department_referral],
        )
        self.assert_list(
            {
                "encounter": str(self.encounter.external_id),
                "patient": str(self.other_patient.external_id),
            },
            [],
        )

    def test_referral_patient_list_includes_encounters_without_encounter_permissions(
        self,
    ):
        self.grant_patient()
        encounter_referral = self.make_referral(encounter=self.encounter)
        other_origin = self.create_facility(user=self.publisher)
        other_encounter = self.create_encounter(
            patient=self.patient,
            facility=other_origin,
            organization=other_origin.default_internal_organization,
        )
        other_referral = self.make_referral(encounter=other_encounter)
        self.make_referral(patient=self.other_patient)
        self.assert_list(
            {"patient": str(self.patient.external_id)},
            [self.referral, encounter_referral, other_referral],
        )

    def test_referral_entity_scope_authorizes_once_and_optional_scopes_only_narrow(
        self,
    ):
        self.grant_destination()
        encounter_referral = self.make_referral(encounter=self.encounter)
        self.make_referral(patient=self.other_patient)
        with (
            patch.object(
                ReferralAccess,
                "can_read_referral",
                autospec=True,
                side_effect=AssertionError("The entity scope authorizes this list"),
            ),
            patch.object(
                ReferralAccess,
                "can_list_encounter_referrals",
                autospec=True,
                side_effect=AssertionError("Encounter is only a narrowing filter"),
            ),
            patch.object(
                ReferralAccess,
                "can_list_patient_referrals",
                autospec=True,
                side_effect=AssertionError("Patient is only a narrowing filter"),
            ),
        ):
            self.assert_list(
                {
                    **self.entity_scope(),
                    "encounter": str(self.encounter.external_id),
                    "patient": str(self.patient.external_id),
                },
                [encounter_referral],
            )
            self.assert_list(
                {
                    **self.entity_scope(),
                    "encounter": str(self.encounter.external_id),
                    "patient": str(self.other_patient.external_id),
                },
                [],
            )
            self.assert_list(
                {**self.entity_scope(), "patient": str(self.patient.external_id)},
                [self.referral, encounter_referral],
            )

    def test_referral_entity_scope_takes_precedence_over_an_authorized_encounter(self):
        self.grant_origin()
        response = self.client.get(
            reverse("referral-list"),
            {**self.entity_scope(), "encounter": str(self.encounter.external_id)},
        )
        self.assertEqual(response.status_code, 403, response.data)

    def test_referral_scoped_lists_preserve_filters_ordering_and_pagination(self):
        self.grant_destination()
        completed = self.make_referral(status="completed")
        in_progress = self.make_referral(status="in_progress")
        response = self.client.get(
            reverse("referral-list"),
            {**self.entity_scope(), "ordering": "status", "limit": 1, "offset": 1},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(in_progress.external_id)],
        )
        self.assert_list({**self.entity_scope(), "pending": False}, [completed])
        self.assert_list({**self.entity_scope(), "status": "pending"}, [self.referral])

    def test_referral_retrieve_update_and_references_keep_working_without_list_scope(
        self,
    ):
        self.grant_origin(
            permissions=[
                ReferralPermissions.can_read_referral.name,
                ReferralPermissions.can_write_referral.name,
            ]
        )
        referral = self.make_referral(encounter=self.encounter)
        referencing = self.make_referral(encounter=self.encounter)
        ReferralResource.objects.create(
            referral=referencing,
            resource_type="referral",
            resource_id=referral.external_id,
        )
        url = reverse("referral-detail", kwargs={"external_id": referral.external_id})
        detail = self.client.get(url)
        self.assertEqual(detail.status_code, 200, detail.data)
        updated = self.client.patch(url, {"status": "completed"}, format="json")
        self.assertEqual(updated.status_code, 200, updated.data)
        references = self.client.get(
            reverse(
                "referral-referenced-by", kwargs={"external_id": referral.external_id}
            )
        )
        self.assertEqual(references.status_code, 200, references.data)
        self.assertEqual(
            [item["id"] for item in references.data["results"]],
            [str(referencing.external_id)],
        )

    def test_referral_create_does_not_require_list_scope_parameters(self):
        self.grant_origin(
            permissions=[
                ReferralPermissions.can_create_referral.name,
                ReferralPermissions.can_read_referral.name,
            ]
        )
        question_id = str(uuid.uuid4())
        questionnaire = baker.make(
            Questionnaire,
            subject_type="encounter",
            status="active",
            questions=[
                {
                    "id": question_id,
                    "link_id": "reason",
                    "text": "Reason for referral",
                    "type": "text",
                    "required": True,
                }
            ],
        )
        self.availability.questionnaires.add(questionnaire)
        response = self.client.post(
            reverse("referral-list"),
            {
                "title": "No list scope needed",
                "availability": str(self.availability.external_id),
                "encounter": str(self.encounter.external_id),
                "questionnaire": str(questionnaire.external_id),
                "questionnaire_response": {
                    "results": [
                        {
                            "question_id": question_id,
                            "values": [{"value": "Specialist assessment"}],
                        }
                    ]
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_referral_retrieve_checks_read_permission_and_preserves_missing_objects(
        self,
    ):
        url = reverse(
            "referral-detail", kwargs={"external_id": self.referral.external_id}
        )
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.grant_patient()
        allowed = self.client.get(url)
        self.assertEqual(allowed.status_code, 200, allowed.data)
        missing = self.client.get(
            reverse("referral-detail", kwargs={"external_id": uuid.uuid4()})
        )
        self.assertEqual(missing.status_code, 404, missing.data)
        self.referral.deleted = True
        self.referral.save(update_fields=["deleted"])
        deleted = self.client.get(url)
        self.assertEqual(deleted.status_code, 404, deleted.data)

    def test_referral_write_permission_does_not_require_read_for_mutations(self):
        self.grant_destination(
            permissions=[ReferralPermissions.can_write_referral.name]
        )
        detail_url = reverse(
            "referral-detail", kwargs={"external_id": self.referral.external_id}
        )
        notes_url = reverse(
            "referral-note-list",
            kwargs={"referral_external_id": self.referral.external_id},
        )
        with patch.object(
            ReferralAccess,
            "can_read_referral",
            autospec=True,
            side_effect=AssertionError("Referral mutations authorize write only"),
        ):
            for method in (self.client.patch, self.client.put):
                updated = method(detail_url, {"status": "in_progress"}, format="json")
                self.assertEqual(updated.status_code, 200, updated.data)
                self.assertEqual(updated.data["status"], "in_progress")
            assigned = self.client.post(
                reverse(
                    "referral-set-assignees",
                    kwargs={"external_id": self.referral.external_id},
                ),
                {
                    "members": [
                        {
                            "user_id": str(self.user.external_id),
                            "role": {
                                "system": "http://snomed.info/sct",
                                "code": "doctor",
                            },
                        }
                    ]
                },
                format="json",
            )
            self.assertEqual(assigned.status_code, 200, assigned.data)
            self.referral.refresh_from_db()
            self.assertEqual(self.referral.assignee_users, [self.user.id])
            thread_url = reverse(
                "referral-thread", kwargs={"external_id": self.referral.external_id}
            )
            created_thread = self.client.post(
                thread_url, {"title": "Referral discussion"}, format="json"
            )
            self.assertEqual(created_thread.status_code, 200, created_thread.data)
            updated_thread = self.client.put(
                thread_url, {"title": "Updated discussion"}, format="json"
            )
            self.assertEqual(updated_thread.status_code, 200, updated_thread.data)
            self.assertEqual(updated_thread.data["title"], "Updated discussion")
            created_note = self.client.post(
                notes_url, {"message": "Write-only discussion note"}, format="json"
            )
            self.assertEqual(created_note.status_code, 200, created_note.data)
            note_url = reverse(
                "referral-note-detail",
                kwargs={
                    "referral_external_id": self.referral.external_id,
                    "external_id": created_note.data["id"],
                },
            )
            for method in (self.client.patch, self.client.put):
                message = f"Updated with {method.__name__}"
                updated_note = method(note_url, {"message": message}, format="json")
                self.assertEqual(updated_note.status_code, 200, updated_note.data)
                self.assertEqual(updated_note.data["message"], message)
            note = NoteMessage.objects.get(external_id=created_note.data["id"])
            self.assertEqual(note.created_by_id, self.user.id)
            self.referral.refresh_from_db()
            other_note = NoteMessage.objects.create(
                thread_id=self.referral.thread_id,
                message="Another author's note",
                created_by=self.other_user,
                updated_by=self.other_user,
            )
            other_note_url = reverse(
                "referral-note-detail",
                kwargs={
                    "referral_external_id": self.referral.external_id,
                    "external_id": other_note.external_id,
                },
            )
            for method in (self.client.patch, self.client.put):
                denied = method(
                    other_note_url,
                    {"message": "Unauthorized author change"},
                    format="json",
                )
                self.assertEqual(denied.status_code, 403, denied.data)
            other_note.refresh_from_db()
            self.assertEqual(other_note.message, "Another author's note")
        for url in (
            detail_url,
            notes_url,
            note_url,
            reverse(
                "referral-questionnaires",
                kwargs={"external_id": self.referral.external_id},
            ),
            reverse(
                "referral-referenced-by",
                kwargs={"external_id": self.referral.external_id},
            ),
        ):
            with self.subTest(url=url):
                denied = self.client.get(url)
                self.assertEqual(denied.status_code, 403, denied.data)

    def test_reverse_referral_requires_target_read_without_authorizing_each_parent(
        self,
    ):
        # A completed encounter does not also grant patient-level access.
        self.encounter.status = "completed"
        self.encounter.save(update_fields=["status"])
        target_membership = self.grant_patient()
        restricted_destination = self.create_facility(user=self.publisher)
        restricted_availability = self.make_availability(
            facility=restricted_destination
        )
        readable_parent = self.make_referral(availability=restricted_availability)
        restricted_parent = self.make_referral(
            availability=restricted_availability, encounter=self.encounter
        )
        wrong_patient = self.make_referral(
            availability=restricted_availability, patient=self.other_patient
        )
        for parent in (readable_parent, restricted_parent, wrong_patient):
            ReferralResource.objects.create(
                referral=parent,
                resource_type="referral",
                resource_id=self.referral.external_id,
            )
        url = reverse(
            "referral-referenced-by", kwargs={"external_id": self.referral.external_id}
        )
        read_referral = ReferralAccess.can_read_referral

        def authorize_target(access, user, referral):
            self.assertEqual(referral.id, self.referral.id)
            return read_referral(access, user, referral)

        def assert_references(params=None):
            with patch.object(
                ReferralAccess,
                "can_read_referral",
                autospec=True,
                side_effect=authorize_target,
            ):
                return self.assert_list(
                    params or {}, [readable_parent, restricted_parent], url=url
                )

        assert_references()
        parent_url = reverse(
            "referral-detail", kwargs={"external_id": restricted_parent.external_id}
        )
        denied_parent = self.client.get(parent_url)
        self.assertEqual(denied_parent.status_code, 403, denied_parent.data)
        parent_membership = self.grant_origin()
        assert_references({"limit": 1, "offset": 100})
        allowed_parent = self.client.get(parent_url)
        self.assertEqual(allowed_parent.status_code, 200, allowed_parent.data)
        parent_membership.delete()
        response = assert_references()
        self.assertNotIn(str(wrong_patient.external_id), str(response.data))
        denied_parent = self.client.get(parent_url)
        self.assertEqual(denied_parent.status_code, 403, denied_parent.data)
        self.grant_origin()
        target_membership.delete()
        denied = self.client.get(url)
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertNotIn(str(restricted_parent.external_id), str(denied.data))

    def test_assigned_referral_list_uses_cached_membership_without_scope_permissions(
        self,
    ):
        self.assign(self.referral, self.user, self.other_user)
        own_only = self.make_referral(status="completed")
        self.assign(own_only, self.user)
        other_only = self.make_referral()
        self.assign(other_only, self.other_user)
        self.make_referral()
        with (
            patch.object(
                ReferralAccess,
                "can_read_referral",
                autospec=True,
                side_effect=AssertionError(
                    "Assignment list needs no referral permission"
                ),
            ),
            patch.object(
                ReferralAccess,
                "check_referral_entity_permission",
                autospec=True,
                side_effect=AssertionError(
                    "Assignment list needs no entity permission"
                ),
            ),
            patch.object(
                ReferralAccess,
                "check_referral_origin_permission",
                autospec=True,
                side_effect=AssertionError(
                    "Assignment list needs no patient permission"
                ),
            ),
        ):
            self.assert_list(
                {}, [self.referral, own_only], url=reverse("referral-assigned-list")
            )

    def test_assigned_referral_filters_and_pagination_cannot_widen_current_user_scope(
        self,
    ):
        self.assign(self.referral, self.user, self.other_user)
        completed = self.make_referral(status="completed")
        self.assign(completed, self.user)
        other_only = self.make_referral()
        self.assign(other_only, self.other_user)
        url = reverse("referral-assigned-list")
        self.assert_list(
            {"assigned_to": str(self.other_user.external_id)}, [self.referral], url=url
        )
        self.assert_list({"assigned_to_me": False}, [self.referral, completed], url=url)
        self.assert_list({"pending": True}, [self.referral], url=url)
        self.assert_list({"status": "completed"}, [completed], url=url)
        self.assert_list({"patient": str(self.other_patient.external_id)}, [], url=url)
        self.assert_list({"facility": str(self.origin.external_id)}, [], url=url)
        response = self.client.get(url, {"ordering": "status", "limit": 1, "offset": 1})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(self.referral.external_id)],
        )

    def test_assigned_referral_list_changes_after_cached_membership_is_removed(self):
        self.assign(self.referral, self.user, self.other_user)
        url = reverse("referral-assigned-list")
        self.assert_list({}, [self.referral], url=url)
        self.assign(self.referral, self.other_user)
        self.referral.refresh_from_db()
        self.assertEqual(self.referral.assignee_users, [self.other_user.id])
        self.assert_list({}, [], url=url)

    def test_assignment_does_not_grant_other_referral_api_permissions(self):
        self.assign(self.referral, self.user)
        self.assert_list({}, [self.referral], url=reverse("referral-assigned-list"))
        detail_url = reverse(
            "referral-detail", kwargs={"external_id": self.referral.external_id}
        )
        for response in (
            self.client.get(detail_url),
            self.client.patch(detail_url, {"status": "completed"}, format="json"),
            self.client.get(reverse("referral-list"), self.entity_scope()),
        ):
            self.assertIn(response.status_code, (403, 404), response.data)

    def test_assigned_referral_route_is_authenticated_and_list_only(self):
        self.assign(self.referral, self.user)
        url = reverse("referral-assigned-list")
        for method in (
            self.client.post,
            self.client.put,
            self.client.patch,
            self.client.delete,
        ):
            response = method(url, {}, format="json")
            self.assertEqual(response.status_code, 405, response.data)
        self.client.force_authenticate(user=None)
        response = self.client.get(url)
        self.assertIn(response.status_code, (401, 403), response.data)
