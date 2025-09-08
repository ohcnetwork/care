from datetime import UTC, datetime

from django.urls import reverse
from model_bakery import baker

from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
)
from care.emr.resources.service_request.spec import (
    ServiceRequestIntentChoices,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
)
from care.security.permissions.service_request import ServiceRequestPermissions
from care.utils.tests.base import CareAPITestBase


class TestServiceRequestApi(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.facility_location = self.create_facility_location(facility=self.facility)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
        )
        self.healthcare_service = baker.make(
            "emr.HealthcareService",
            facility=self.facility,
        )
        self.activity_definition = baker.make(
            "emr.ActivityDefinition",
            facility=self.facility,
        )
        self.client.force_authenticate(user=self.user)

        self.base_url = reverse(
            "service_request-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        self.valid_code = {
            "display": "Test Service Code",
            "system": "http://test_system.care/service",
            "code": "test_service_123",
        }

    def _get_service_request_url(self, service_request_id):
        """Helper to get the detail URL for a specific service request."""
        return reverse(
            "service_request-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": service_request_id,
            },
        )

    def create_service_request(self, **kwargs):
        """Create a service request instance using baker."""
        data = {
            "patient": self.patient,
            "facility": self.facility,
            "encounter": self.encounter,
            "title": "Test Service Request",
            "status": ServiceRequestStatusChoices.active.value,
            "intent": ServiceRequestIntentChoices.order.value,
            "priority": ServiceRequestPriorityChoices.routine.value,
            "category": ActivityDefinitionCategoryOptions.laboratory.value,
            "code": self.valid_code,
            "do_not_perform": False,
        }
        data.update(kwargs)
        return baker.make("emr.ServiceRequest", **data)

    def get_service_request_data(self, **kwargs):
        """Get valid service request API data."""
        # Set default requester to the current test user if not specified
        if "requester" not in kwargs:
            kwargs["requester"] = self.user.external_id

        data = {
            "title": "Test Service Request",
            "status": ServiceRequestStatusChoices.active.value,
            "intent": ServiceRequestIntentChoices.order.value,
            "priority": ServiceRequestPriorityChoices.routine.value,
            "category": ActivityDefinitionCategoryOptions.laboratory.value,
            "code": self.valid_code,
            "encounter": self.encounter.external_id,
            "do_not_perform": False,
            "note": "Test note",
            "patient_instruction": "Test patient instruction",
            "locations": [self.facility_location.external_id],
        }
        data.update(kwargs)
        return data

    def create_facility_location(self, **kwargs):
        """Create a facility location for testing."""
        from care.emr.models.location import FacilityLocation

        data = {
            "name": "Test facility Location",
            "facility": self.facility,
            "status": "active",
            "facility_organization_cache": [self.organization.id],
        }
        data.update(kwargs)
        return baker.make(FacilityLocation, **data)

    def test_list_service_request_with_permissions(self):
        """
        Users with can_read_service_request permission can list service requests (HTTP 200).
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Create a service request to list
        self.create_service_request()

        # Test listing by encounter (simpler permission check)
        response = self.client.get(
            self.base_url + f"?encounter={self.encounter.external_id}"
        )
        self.assertEqual(response.status_code, 200)

    def test_list_service_request_without_permissions(self):
        """
        Users without can_read_service_request permission => (HTTP 403).
        """
        response = self.client.get(
            self.base_url + f"?location={self.facility_location.external_id}"
        )
        self.assertEqual(response.status_code, 403)

    def test_list_service_request_missing_location_or_encounter(self):
        """
        Listing service requests requires either location or encounter parameter.
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Location or encounter is required", status_code=400
        )

    def test_create_service_request_with_permission(self):
        """
        Users with can_write_service_request permission can create service requests (HTTP 200).
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_service_request_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_service_request_without_permission(self):
        """
        Users without can_write_service_request permission => (HTTP 403).
        """
        data = self.get_service_request_data()
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_service_request_with_valid_healthcare_service(self):
        """
        Service requests can be created with a valid healthcare service from the same facility.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_service_request_data(
            healthcare_service=self.healthcare_service.external_id
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_service_request_with_healthcare_service_different_facility(self):
        """
        Service requests cannot be created with healthcare service from different facility.
        """
        other_facility = self.create_facility(user=self.user)
        other_healthcare_service = baker.make(
            "emr.HealthcareService",
            facility=other_facility,
        )

        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_service_request_data(
            healthcare_service=other_healthcare_service.external_id
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Healthcare Service must be from the same facility",
            status_code=400,
        )

    def test_create_service_request_with_valid_requester(self):
        """
        Service requests can be created with a valid requester who is member of facility.
        """
        requester = self.create_user()

        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)
        self.attach_role_facility_organization_user(self.organization, requester, role)

        data = self.get_service_request_data(requester=requester.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_service_request_with_requester_not_facility_member(self):
        """
        Service requests cannot be created with requester who is not a facility member.
        """
        requester = self.create_user()

        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_service_request_data(requester=requester.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "requester must be a member of the facility", status_code=400
        )

    def test_create_service_request_with_invalid_location(self):
        """
        Service requests cannot be created with invalid location ID.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        invalid_location_id = "550e8400-e29b-41d4-a716-446655440000"
        data = self.get_service_request_data(locations=[invalid_location_id])
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Location with id {invalid_location_id} not found",
            status_code=400,
        )

    def test_create_service_request_with_completed_encounter(self):
        """
        Service requests cannot be created for completed encounters.
        """
        completed_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.organization,
            status="completed",
        )

        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_service_request_data(encounter=completed_encounter.external_id)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_retrieve_service_request_with_permission(self):
        """
        Users with can_read_service_request permission can retrieve service requests.
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        service_request = self.create_service_request()
        url = self._get_service_request_url(service_request.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(service_request.external_id))

    def test_retrieve_service_request_without_permission(self):
        """
        Users without can_read_service_request permission => (HTTP 403).
        """
        service_request = self.create_service_request()
        url = self._get_service_request_url(service_request.external_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_update_service_request_with_permission(self):
        """
        Users with can_write_service_request permission can update service requests.
        """
        permissions = [
            ServiceRequestPermissions.can_read_service_request.name,
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        service_request = self.create_service_request()
        url = self._get_service_request_url(service_request.external_id)
        data = self.get_service_request_data(title="Updated Service Request")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_update_service_request_without_permission(self):
        """
        Users without can_write_service_request permission => (HTTP 403).
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        service_request = self.create_service_request()
        url = self._get_service_request_url(service_request.external_id)
        data = self.get_service_request_data(title="Updated Service Request")
        response = self.client.put(url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_service_request_filtering_by_status(self):
        """
        Test filtering service requests by status.
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_service_request(status=ServiceRequestStatusChoices.active.value)
        self.create_service_request(status=ServiceRequestStatusChoices.completed.value)

        response = self.client.get(
            self.base_url + f"?encounter={self.encounter.external_id}&status=active"
        )
        self.assertEqual(response.status_code, 200)

    def test_service_request_filtering_by_category(self):
        """
        Test filtering service requests by category.
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_service_request(
            category=ActivityDefinitionCategoryOptions.laboratory.value
        )
        self.create_service_request(
            category=ActivityDefinitionCategoryOptions.imaging.value
        )

        response = self.client.get(
            self.base_url
            + f"?encounter={self.encounter.external_id}&category=laboratory"
        )
        self.assertEqual(response.status_code, 200)

    def test_service_request_filtering_by_priority(self):
        """
        Test filtering service requests by priority.
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_service_request(priority=ServiceRequestPriorityChoices.urgent.value)
        self.create_service_request(
            priority=ServiceRequestPriorityChoices.routine.value
        )

        response = self.client.get(
            self.base_url + f"?encounter={self.encounter.external_id}&priority=urgent"
        )
        self.assertEqual(response.status_code, 200)

    def test_service_request_filtering_by_do_not_perform(self):
        """
        Test filtering service requests by do_not_perform flag.
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_service_request(do_not_perform=True)
        self.create_service_request(do_not_perform=False)

        response = self.client.get(
            self.base_url
            + f"?encounter={self.encounter.external_id}&do_not_perform=true"
        )
        self.assertEqual(response.status_code, 200)

    def test_service_request_ordering_by_created_date(self):
        """
        Test ordering service requests by created_date.
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        self.create_service_request()

        response = self.client.get(
            self.base_url
            + f"?encounter={self.encounter.external_id}&ordering=created_date"
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.get(
            self.base_url
            + f"?encounter={self.encounter.external_id}&ordering=-created_date"
        )
        self.assertEqual(response.status_code, 200)

    def test_apply_activity_definition_action(self):
        """
        Test applying activity definition to create service request.
        """
        permissions = [
            ServiceRequestPermissions.can_read_service_request.name,
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        apply_url = reverse(
            "service_request-apply-activity-definition",
            kwargs={"facility_external_id": self.facility.external_id},
        )

        data = {
            "activity_definition": str(self.activity_definition.external_id),
            "encounter": str(self.encounter.external_id),
            "service_request": {
                "title": "Applied Service Request",
                "status": ServiceRequestStatusChoices.active.value,
                "intent": ServiceRequestIntentChoices.order.value,
                "priority": ServiceRequestPriorityChoices.routine.value,
                "category": ActivityDefinitionCategoryOptions.laboratory.value,
                "code": self.valid_code,
                "do_not_perform": False,
                "locations": [self.facility_location.external_id],
            },
        }

        response = self.client.post(apply_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_specimen_action(self):
        """
        Test creating specimen from service request.
        """
        from care.security.permissions.specimen import SpecimenPermissions

        permissions = [
            ServiceRequestPermissions.can_read_service_request.name,
            SpecimenPermissions.can_write_specimen.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        service_request = self.create_service_request()
        create_specimen_url = reverse(
            "service_request-create-specimen",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": service_request.external_id,
            },
        )

        data = {
            "specimen_type": {
                "display": "Blood Sample",
                "system": "http://test_system.care/specimen",
                "code": "blood_sample",
            },
            "status": "available",
            "collection_datetime": datetime.now(UTC).isoformat(),
        }

        response = self.client.post(create_specimen_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_create_specimen_without_permission(self):
        """
        Test creating specimen without proper permissions => (HTTP 403).
        """
        permissions = [ServiceRequestPermissions.can_read_service_request.name]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        service_request = self.create_service_request()
        create_specimen_url = reverse(
            "service_request-create-specimen",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": service_request.external_id,
            },
        )

        data = {
            "specimen_type": {
                "display": "Blood Sample",
                "system": "http://test_system.care/specimen",
                "code": "blood_sample",
            },
            "status": "available",
            "collection_datetime": datetime.now(UTC).isoformat(),
        }

        response = self.client.post(create_specimen_url, data, format="json")
        self.assertEqual(response.status_code, 403)

    def test_create_specimen_from_definition_action(self):
        """
        Test creating specimen from specimen definition.
        """
        from care.security.permissions.specimen import SpecimenPermissions

        permissions = [
            ServiceRequestPermissions.can_read_service_request.name,
            SpecimenPermissions.can_write_specimen.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        specimen_definition = baker.make(
            "emr.SpecimenDefinition",
            facility=self.facility,
        )
        service_request = self.create_service_request()

        create_specimen_url = reverse(
            "service_request-create-specimen-from-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": service_request.external_id,
            },
        )

        data = {
            "specimen_definition": str(specimen_definition.external_id),
            "specimen": {
                "status": "available",
                "collection_datetime": datetime.now(UTC).isoformat(),
                "specimen_type": {
                    "display": "Blood Sample",
                    "system": "http://test_system.care/specimen",
                    "code": "blood_sample",
                },
            },
        }

        response = self.client.post(create_specimen_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_superuser_can_list_all_service_requests(self):
        """
        Superuser can list service requests without location/encounter filters.
        """
        self.client.force_authenticate(user=self.superuser)
        self.create_service_request()

        response = self.client.get(self.base_url)
        self.assertEqual(response.status_code, 200)

    def test_service_request_validation_required_fields(self):
        """
        Test validation of required fields for service request creation.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Test without title
        data = self.get_service_request_data()
        del data["title"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)

        # Test without status
        data = self.get_service_request_data()
        del data["status"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)

        # Test without encounter
        data = self.get_service_request_data()
        del data["encounter"]
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_service_request_status_choices_validation(self):
        """
        Test validation of service request status choices.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Valid status
        data = self.get_service_request_data(
            status=ServiceRequestStatusChoices.active.value
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        # Invalid status
        data = self.get_service_request_data(status="invalid_status")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_service_request_intent_choices_validation(self):
        """
        Test validation of service request intent choices.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Valid intent
        data = self.get_service_request_data(
            intent=ServiceRequestIntentChoices.plan.value
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        # Invalid intent
        data = self.get_service_request_data(intent="invalid_intent")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_service_request_priority_choices_validation(self):
        """
        Test validation of service request priority choices.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        # Valid priority
        data = self.get_service_request_data(
            priority=ServiceRequestPriorityChoices.urgent.value
        )
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

        # Invalid priority
        data = self.get_service_request_data(priority="invalid_priority")
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_service_request_with_occurrence_datetime(self):
        """
        Test service request with occurrence datetime field.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        data = self.get_service_request_data(occurance=datetime.now(UTC).isoformat())
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)

    def test_service_request_with_body_site(self):
        """
        Test service request with body site specification.
        """
        permissions = [
            ServiceRequestPermissions.can_write_service_request.name,
        ]
        role = self.create_role_with_permissions(permissions)
        self.attach_role_facility_organization_user(self.organization, self.user, role)

        body_site = {
            "display": "Left arm",
            "system": "http://snomed.info/sct",
            "code": "368209003",
        }
        data = self.get_service_request_data(body_site=body_site)
        response = self.client.post(self.base_url, data, format="json")
        self.assertEqual(response.status_code, 200)
