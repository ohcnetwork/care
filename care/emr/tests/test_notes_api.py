from django.urls import reverse
from model_bakery import baker

from care.emr.models.notes import NoteMessage, NoteThread
from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class NoteThreadApiTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)

    def _get_thread_list_url(self):
        return reverse(
            "thread-list",
            kwargs={"patient_external_id": self.patient.external_id},
        )

    def _get_thread_detail_url(self, thread_external_id):
        return reverse(
            "thread-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "external_id": thread_external_id,
            },
        )

    def _create_thread(self, encounter=None):
        return baker.make(
            NoteThread,
            patient=self.patient,
            encounter=encounter,
            _fill_optional=True,
        )

    def test_list_threads_on_patient(self):
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_view_clinical_data.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        url = self._get_thread_list_url()
        thread = self._create_thread()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, thread.title, status_code=200)

    def test_list_threads_on_patient_without_permission(self):
        url = self._get_thread_list_url()
        self._create_thread()
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(response, "Permission denied to user", status_code=403)

    def test_list_threads_on_encounter(self):
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_view_clinical_data.name,
                EncounterPermissions.can_read_encounter.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        url = f"{self._get_thread_list_url()}?encounter={self.encounter.external_id}"
        thread = self._create_thread(encounter=self.encounter)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, thread.title, status_code=200)

    def test_create_thread_on_patient(self):
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_write_patient.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        url = self._get_thread_list_url()
        data = {"title": "Test Thread"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, data["title"], status_code=200)

    def test_create_thread_on_patient_without_permission(self):
        url = self._get_thread_list_url()
        data = {"title": "Test Thread"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(
            response, "You do not have permission for this action", status_code=403
        )

    def test_create_thread_on_encounter_with_permission(self):
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_write_encounter.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        url = self._get_thread_list_url()
        data = {
            "title": "Test Thread",
            "encounter": self.encounter.external_id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, data["title"], status_code=200)

    def test_create_thread_on_encounter_without_permission(self):
        url = self._get_thread_list_url()
        data = {
            "title": "Test Thread",
            "encounter": self.encounter.external_id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(
            response, "You do not have permission for this action", status_code=403
        )

    def test_create_thread_on_encounter_with_patient_mismatch(self):
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_write_encounter.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        url = self._get_thread_list_url()
        encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=self.facility,
            organization=self.facility_organization,
        )
        data = {
            "title": "Test Thread",
            "encounter": encounter.external_id,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertContains(response, "Patient Mismatch", status_code=400)

    def test_update_thread(self):
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_view_clinical_data.name,
                PatientPermissions.can_write_patient.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        thread = self._create_thread()
        url = self._get_thread_detail_url(thread.external_id)
        data = {
            "title": "Updated Thread",
            "created_date": thread.created_date.isoformat(),
            "modified_date": thread.modified_date.isoformat(),
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        thread.refresh_from_db()
        self.assertEqual(thread.title, data["title"])

    def test_update_thread_without_permission(self):
        thread = self._create_thread()
        url = self._get_thread_detail_url(thread.external_id)
        data = {
            "title": "Updated Thread",
            "created_date": thread.created_date.isoformat(),
            "modified_date": thread.modified_date.isoformat(),
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(response, "Permission denied to user", status_code=403)


class NoteMessageApiTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.patient = self.create_patient()
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        self.client.force_authenticate(user=self.user)

    def _get_note_list_url(self, thread_external_id):
        return reverse(
            "note-list",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "thread_external_id": thread_external_id,
            },
        )

    def _get_note_detail_url(self, thread_external_id, note_external_id):
        return reverse(
            "note-detail",
            kwargs={
                "patient_external_id": self.patient.external_id,
                "thread_external_id": thread_external_id,
                "external_id": note_external_id,
            },
        )

    def _create_thread(self, encounter=None):
        return baker.make(
            NoteThread,
            patient=self.patient,
            encounter=encounter,
            _fill_optional=True,
        )

    def _create_note(self, thread):
        return baker.make(
            NoteMessage,
            thread=thread,
            created_by=self.user,
            _fill_optional=True,
        )

    def test_list_notes_on_thread(self):
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_view_clinical_data.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        thread = self._create_thread()
        note = self._create_note(thread)
        url = self._get_note_list_url(thread.external_id)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, note.message, status_code=200)

    def test_list_notes_on_thread_without_permission(self):
        thread = self._create_thread()
        self._create_note(thread)
        url = self._get_note_list_url(thread.external_id)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(response, "Permission denied to user", status_code=403)

    def test_list_notes_on_encounter(self):
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_view_clinical_data.name,
                EncounterPermissions.can_read_encounter.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        thread = self._create_thread(encounter=self.encounter)
        url = f"{self._get_note_list_url(thread.external_id)}?encounter={self.encounter.external_id}"
        note = self._create_note(thread)
        response = self.client.get(url, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, note.message, status_code=200)

    def test_create_note_on_encounter_with_permission(self):
        role = self.create_role_with_permissions(
            permissions=[EncounterPermissions.can_write_encounter.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        thread = self._create_thread(encounter=self.encounter)
        url = self._get_note_list_url(thread.external_id)
        data = {"message": "Test Note", "encounter": self.encounter.external_id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, data["message"], status_code=200)

    def test_create_note_on_encounter_without_permission(self):
        thread = self._create_thread(encounter=self.encounter)
        url = self._get_note_list_url(thread.external_id)
        data = {"message": "Test Note", "encounter": self.encounter.external_id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(
            response, "You do not have permission for this action", status_code=403
        )

    def test_create_note_on_encounter_with_patient_mismatch(self):
        role = self.create_role_with_permissions(
            permissions=[
                EncounterPermissions.can_write_encounter.name,
                PatientPermissions.can_write_patient.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        thread = self._create_thread()
        encounter = self.create_encounter(
            patient=self.create_patient(),
            facility=self.facility,
            organization=self.facility_organization,
        )
        url = self._get_note_list_url(thread.external_id)
        data = {"message": "Test Note", "encounter": encounter.external_id}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertContains(response, "Patient Mismatch", status_code=400)

    def test_create_note_on_thread(self):
        role = self.create_role_with_permissions(
            permissions=[PatientPermissions.can_write_patient.name]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        thread = self._create_thread()
        url = self._get_note_list_url(thread.external_id)
        data = {"message": "Test Note"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertContains(response, data["message"], status_code=200)

    def test_create_note_on_thread_without_permission(self):
        thread = self._create_thread()
        url = self._get_note_list_url(thread.external_id)
        data = {"message": "Test Note"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(
            response, "You do not have permission for this action", status_code=403
        )

    def test_update_note(self):
        role = self.create_role_with_permissions(
            permissions=[
                PatientPermissions.can_view_clinical_data.name,
                PatientPermissions.can_write_patient.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        thread = self._create_thread()
        note = self._create_note(thread)
        url = self._get_note_detail_url(thread.external_id, note.external_id)
        data = {
            "message": "Updated Note",
            "created_date": note.created_date.isoformat(),
            "modified_date": note.modified_date.isoformat(),
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        note.refresh_from_db()
        self.assertEqual(note.message, data["message"])

    def test_update_note_without_permission(self):
        thread = self._create_thread()
        note = self._create_note(thread)
        url = self._get_note_detail_url(thread.external_id, note.external_id)
        data = {
            "message": "Updated Note",
            "created_date": note.created_date.isoformat(),
            "modified_date": note.modified_date.isoformat(),
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertContains(response, "Permission denied to user", status_code=403)

    def test_create_note_after_encounter_complete(self):
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
        )
        role = self.create_role_with_permissions(
            permissions=[
                EncounterPermissions.can_write_encounter.name,
                PatientPermissions.can_write_patient.name,
            ]
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, role
        )
        encounter.status = "completed"
        encounter.save()
        thread = self._create_thread(encounter=encounter)

        url = self._get_note_list_url(thread.external_id)
        data = {"message": "Late Note"}
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403, response.data)
