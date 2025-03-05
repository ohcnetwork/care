from django.urls import reverse
from rest_framework import status

from care.security.permissions.encounter import EncounterPermissions
from care.security.permissions.patient import PatientPermissions
from care.utils.tests.base import CareAPITestBase


class TestMetaArtifactViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.patient = self.create_patient()
        self.organization = self.create_facility_organization(facility=self.facility)
        self.encounter = self.create_encounter(
            patient=self.patient, facility=self.facility, organization=self.organization
        )
        self.client.force_authenticate(user=self.user)
        self.base_url = reverse("meta_artifacts-list")
        self.excalidraw_object_value = {
            "elements": [
                {
                    "type": "rectangle",
                    "x": 10,
                    "y": 10,
                    "width": 100,
                    "height": 100,
                    "fillColor": "#ffffff",
                }
            ]
        }

    def generate_meta_artifact_data(self, **kwargs):
        return {
            "associating_type": "patient",
            "associating_id": self.patient.external_id,
            "name": "Test Meta Artifact",
            "object_type": "drawing",
            "object_value": self.excalidraw_object_value,
            "note": "Test Note",
            **kwargs,
        }

    def create_meta_artifact(self, **kwargs):
        from care.emr.models import MetaArtifact

        associating_type = kwargs.pop("associating_type", "patient")
        associating_id = kwargs.pop(
            "associating_external_id",
            (
                self.patient.external_id
                if associating_type == "patient"
                else self.encounter.external_id
            ),
        )
        data = {
            "associating_type": associating_type,
            "associating_external_id": associating_id,
            "name": "Test Meta Artifact",
            "object_type": "drawing",
            "object_value": self.excalidraw_object_value,
            "note": "Test Note",
        }
        data.update(kwargs)
        return MetaArtifact.objects.create(**data)

    def _get_meta_artifact_url(self, meta_artifact_id):
        """Helper to get the detail URL for a specific meta-artifact."""
        return reverse(
            "meta_artifacts-detail", kwargs={"external_id": meta_artifact_id}
        )

    # LIST TESTS
    def test_list_patient_meta_artifacts_with_permission(self):
        """Users with can_view_clinical_data permission can list meta artifacts"""
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(
            self.base_url,
            data={
                "associating_type": "patient",
                "associating_id": self.patient.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_encounter_meta_artifacts_with_permission(self):
        """Users with can_view_clinical_data permission can list meta artifacts"""
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(
            self.base_url,
            data={
                "associating_type": "encounter",
                "associating_id": self.encounter.external_id,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_patient_meta_artifacts_without_permission(self):
        """Users without can_view_clinical_data permission cannot view meta artifacts"""
        response = self.client.get(
            self.base_url,
            data={
                "associating_type": "patient",
                "associating_id": self.patient.external_id,
            },
        )
        self.assertContains(
            response, "Cannot view object", status_code=status.HTTP_403_FORBIDDEN
        )

    def test_list_encounter_meta_artifacts_without_permission(self):
        """Users without can_view_clinical_data permission cannot view meta artifacts"""
        response = self.client.get(
            self.base_url,
            data={
                "associating_type": "encounter",
                "associating_id": self.encounter.external_id,
            },
        )
        self.assertContains(
            response, "Cannot view object", status_code=status.HTTP_403_FORBIDDEN
        )

    def test_list_meta_artifacts_without_associating_information(self):
        """Users cannot list meta artifacts without associating information"""
        response = self.client.get(self.base_url)
        self.assertContains(
            response,
            "'associating_type' and 'associating_id' are required to retrieve meta artifacts",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    def test_list_meta_artifacts_without_associating_type(self):
        """Users cannot list meta artifacts without associating type"""
        response = self.client.get(
            self.base_url, data={"associating_id": self.patient.external_id}
        )

        self.assertContains(
            response,
            "'associating_type' and 'associating_id' are required to retrieve meta artifacts",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    def test_list_meta_artifacts_without_associating_id(self):
        """Users cannot list meta artifacts without associating type"""
        response = self.client.get(self.base_url, data={"associating_type": "patient"})
        self.assertContains(
            response,
            "'associating_type' and 'associating_id' are required to retrieve meta artifacts",
            status_code=status.HTTP_403_FORBIDDEN,
        )

    def test_list_meta_artifacts_filtered_by_object_type(self):
        """Users can filter meta artifacts by multiple object types"""
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        artifact_type1 = self.create_meta_artifact(object_type="type1")
        artifact_type2 = self.create_meta_artifact(object_type="type2")
        artifact_type3 = self.create_meta_artifact(object_type="type3")

        response = self.client.get(
            self.base_url,
            data={
                "associating_type": "patient",
                "associating_id": self.patient.external_id,
                "object_type": "type1,type2",
            },
        )
        self.assertContains(response, artifact_type1.external_id)
        self.assertContains(response, artifact_type2.external_id)
        self.assertNotContains(response, artifact_type3.external_id)

    # CREATE TESTS
    def test_create_meta_artifact_associated_to_patient_with_permission(self):
        """Users with can_write_patient_obj permission can create meta artifact associated to patient"""
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        create_data = self.generate_meta_artifact_data()
        response = self.client.post(self.base_url, create_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_meta_artifact_associated_to_encounter_with_permission(self):
        """Users with can_write_encounter permission can create meta artifact associated to encounter"""
        permissions = [EncounterPermissions.can_write_encounter.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        create_data = self.generate_meta_artifact_data(
            associating_type="encounter", associating_id=self.encounter.external_id
        )
        response = self.client.post(self.base_url, create_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_meta_artifact_associated_to_encounter_without_permission(self):
        """Users without permission cannot create meta artifact associated to encounter"""
        create_data = self.generate_meta_artifact_data()
        response = self.client.post(self.base_url, create_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_meta_artifact_with_incorrect_permission(self):
        """Users without correct permission can create meta artifact associated to encounter"""
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        create_data = self.generate_meta_artifact_data(
            associating_type="encounter", associating_id=self.encounter.external_id
        )
        response = self.client.post(self.base_url, create_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_meta_artifact_without_object_value(self):
        """Users with cannot create meta artifact without object_value"""
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.generate_meta_artifact_data()
        data.pop("object_value")

        response = self.client.post(self.base_url, data=data, format="json")
        self.assertContains(response, status_code=400, text="object_value")
        self.assertContains(response, status_code=400, text="Field required")

    def test_create_meta_artifact_without_name(self):
        """Users cannot create meta artifact without name"""
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        create_data = self.generate_meta_artifact_data(name="")
        response = self.client.post(self.base_url, create_data, format="json")
        self.assertContains(response, status_code=400, text="Name cannot be empty")

    # UPDATE TESTS
    def test_update_meta_artifact_with_permission(self):
        """Users with can_write_patient_obj and can_view_clinical_data permission can update meta artifact"""
        permissions = [
            PatientPermissions.can_write_patient.name,
            PatientPermissions.can_view_clinical_data.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        artifact = self.create_meta_artifact()
        update_url = self._get_meta_artifact_url(artifact.external_id)
        data = {"object_value": self.excalidraw_object_value}
        response = self.client.put(update_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_meta_artifact_without_permission(self):
        """Users without permission cannot update meta artifact"""
        artifact = self.create_meta_artifact()
        update_url = self._get_meta_artifact_url(artifact.external_id)
        data = {"object_value": self.excalidraw_object_value}
        response = self.client.put(update_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # RETRIEVE TESTS
    def test_retrieve_meta_artifact_with_permission(self):
        """Users with can_view_clinical_data permission can view clinical data"""
        permissions = [PatientPermissions.can_view_clinical_data.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        obj = self.create_meta_artifact()
        retrieve_url = self._get_meta_artifact_url(obj.external_id)
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_meta_artifact_without_permission(self):
        obj = self.create_meta_artifact()
        retrieve_url = self._get_meta_artifact_url(obj.external_id)
        response = self.client.get(retrieve_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # UPSERT TEST
    def test_upsert_meta_artifact_with_permission(self):
        """Users with can_write_patient_obj permission can upsert meta artifact objects"""
        permissions = [PatientPermissions.can_write_patient.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        existing_artifact = self.create_meta_artifact()
        create_data = self.generate_meta_artifact_data()
        update_data = {
            "id": existing_artifact.external_id,
            "object_value": self.excalidraw_object_value,
        }
        data = {"datapoints": [create_data, update_data]}

        response = self.client.post(
            reverse("meta_artifacts-upsert"), data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_upsert_meta_artifact_without_permission(self):
        existing_artifact = self.create_meta_artifact()
        create_data = self.generate_meta_artifact_data()
        update_data = {
            "id": existing_artifact.external_id,
            "object_value": self.excalidraw_object_value,
        }
        data = {"datapoints": [create_data, update_data]}

        response = self.client.post(
            reverse("meta_artifacts-upsert"), data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
