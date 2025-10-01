import uuid
from secrets import choice

from django.urls import reverse
from model_bakery import baker

from care.emr.resources.activity_definition.spec import (
    ActivityDefinitionCategoryOptions,
    ActivityDefinitionKindOptions,
)
from care.emr.resources.service_request.spec import (
    ServiceRequestIntentChoices,
    ServiceRequestPriorityChoices,
    ServiceRequestStatusChoices,
)
from care.emr.resources.specimen.spec import SpecimenStatusOptions
from care.emr.resources.specimen_definition.spec import (
    SpecimenDefinitionStatusOptions,
)
from care.security.permissions.service_request import ServiceRequestPermissions
from care.security.permissions.specimen import SpecimenPermissions
from care.utils.tests.base import CareAPITestBase


class TestServiceRequestViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.patient = self.create_patient()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )
        self.facility_location = self.create_facility_location(facility=self.facility)
        self.encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            current_location=self.facility_location,
        )
        self.service_request = self.create_service_request(
            title="Test Service Request",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            status=ServiceRequestStatusChoices.active.value,
            intent=choice(list(ServiceRequestIntentChoices)).value,
            priority=choice(list(ServiceRequestPriorityChoices)).value,
            category=choice(list(ActivityDefinitionCategoryOptions)).value,
        )
        self.role = self.create_role_with_permissions(
            permissions=[
                ServiceRequestPermissions.can_read_service_request.name,
                ServiceRequestPermissions.can_write_service_request.name,
                SpecimenPermissions.can_write_specimen.name,
                SpecimenPermissions.can_read_specimen.name,
            ]
        )
        self.healthcare_service = self.create_healthcare_service(
            facility=self.facility,
            name="Test Healthcare Service",
        )
        self.service_request_data = {
            "title": "Test Service Request",
            "patient": self.patient.external_id,
            "encounter": self.encounter.external_id,
            "status": ServiceRequestStatusChoices.active.value,
            "intent": choice(list(ServiceRequestIntentChoices)).value,
            "priority": choice(list(ServiceRequestPriorityChoices)).value,
            "category": choice(list(ActivityDefinitionCategoryOptions)).value,
            "code": {
                "code": "33747003",
                "system": "http://snomed.info/sct",
                "display": "Glucose measurement",
            },
            "healthcare_service": str(self.healthcare_service.external_id),
            "requester": str(self.user.external_id),
            "locations": [str(self.facility_location.external_id)],
        }
        self.specimen_data = {
            "title": "Test Specimen",
            "patient": str(self.patient.external_id),
            "encounter": str(self.encounter.external_id),
            "service_request": str(self.service_request.external_id),
            "specimen_type": {
                "code": "122555007",
                "display": "Venous blood specimen",
                "system": "http://snomed.info/sct",
            },
            "status": SpecimenStatusOptions.available.value,
        }
        self.url = reverse(
            "service_request-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )

    def get_detail_url(self, facility_external_id, external_id):
        return reverse(
            "service_request-detail",
            kwargs={
                "facility_external_id": facility_external_id,
                "external_id": external_id,
            },
        )

    def create_specimen(self, **kwargs):
        return baker.make(
            "emr.Specimen",
            facility=self.facility,
            patient=self.patient,
            encounter=self.encounter,
            service_request=self.service_request,
            status=SpecimenStatusOptions.available.value,
            **kwargs,
        )

    def create_activity_definition(self, slug=None, **kwargs):
        from care.emr.models import ActivityDefinition

        return baker.make(
            ActivityDefinition,
            facility=self.facility,
            status="active",
            slug=f"f-{self.facility.external_id}-{slug}",
            classification=ActivityDefinitionCategoryOptions.laboratory.value,
            kind=ActivityDefinitionKindOptions.service_request.value,
            **kwargs,
        )

    def create_facility_location(self, facility):
        from care.emr.models.location import FacilityLocation

        return baker.make(
            FacilityLocation,
            name="Test facility Locations",
            facility=facility,
        )

    def create_healthcare_service(self, facility, **kwargs):
        from care.emr.models import HealthcareService

        return baker.make(
            HealthcareService,
            facility=facility,
            **kwargs,
        )

    def create_specimen_definition(self, slug=None, **kwargs):
        from care.emr.models import SpecimenDefinition

        return baker.make(
            SpecimenDefinition,
            facility=self.facility,
            status=SpecimenDefinitionStatusOptions.active.value,
            slug=f"f-{self.facility.external_id}-{slug}",
            **kwargs,
        )

    # test cases for the retrieving a service request

    def test_get_service_request_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(
            self.get_detail_url(
                self.facility.external_id, self.service_request.external_id
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.service_request.external_id))

    def test_get_service_request_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(
                self.facility.external_id, self.service_request.external_id
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(self.service_request.external_id))

    def test_get_service_request_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(
                self.facility.external_id, self.service_request.external_id
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to read this service request",
            response.data["detail"],
        )

    def test_get_invalid_service_request(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.get_detail_url(self.facility.external_id, uuid.uuid4())
        )
        self.assertContains(
            response, "No ServiceRequest matches the given query.", status_code=404
        )

    # test cases for creating a service request

    def test_create_service_request_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        response = self.client.post(
            self.url,
            self.service_request_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"])
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_service_request_as_user_with_permission(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        response = self.client.post(
            self.url,
            self.service_request_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"])
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_service_request_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            self.url,
            self.service_request_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You do not have permission to create a service request for this encounter",
            status_code=403,
        )

    def test_create_service_request_with_invalid_data(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invalid_data = {
            "patient": self.patient.external_id,
            "encounter": self.encounter.external_id,
            "status": ServiceRequestStatusChoices.active.value,
            "intent": choice(list(ServiceRequestIntentChoices)).value,
            "priority": choice(list(ServiceRequestPriorityChoices)).value,
        }
        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_service_request_with_another_facility_healthcare_service(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        another_facility = self.create_facility(user=self.user)
        healthcare_service = self.create_healthcare_service(facility=another_facility)
        self.client.force_authenticate(user=self.user)
        invalid_data = self.service_request_data.copy()
        invalid_data["healthcare_service"] = str(healthcare_service.external_id)
        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_create_service_request_with_invalid_location(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        another_facility = self.create_facility(user=self.user)
        facility_location = self.create_facility_location(facility=another_facility)
        self.client.force_authenticate(user=self.user)
        invalid_data = self.service_request_data.copy()
        invalid_data["locations"] = [str(facility_location.external_id)]
        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            f"Location with id {facility_location.external_id} not found",
            status_code=400,
        )

    def test_create_service_request_with_invalid_healthcare_service(self):
        facility = self.create_facility(user=self.user)
        healthcare_service = self.create_healthcare_service(facility=facility)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        invalid_data = self.service_request_data.copy()
        invalid_data["healthcare_service"] = str(healthcare_service.external_id)
        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "Healthcare Service must be from the same facility",
            status_code=400,
        )

    def test_create_service_request_without_requester(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        invalid_data = self.service_request_data.copy()
        invalid_data["requester"] = None
        response = self.client.post(
            self.url,
            invalid_data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "requester must be a member of the facility",
            status_code=400,
        )

    def test_create_service_request_with_non_facility_member_requester(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        another_user = self.create_user()
        data = self.service_request_data.copy()
        data["requester"] = str(another_user.external_id)
        response = self.client.post(
            self.url,
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response,
            "requester must be a member of the facility",
            status_code=400,
        )

    def test_create_service_request_with_completed_encounter(self):
        self.client.force_authenticate(user=self.user)
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            current_location=self.facility_location,
            status="completed",
        )
        data = self.service_request_data.copy()
        data["encounter"] = str(encounter.external_id)
        response = self.client.post(
            self.url,
            data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You do not have permission to create a service request for this encounter",
            status_code=403,
        )

    # test cases for updating a service request

    def test_update_service_request_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        update_data = {
            "title": "Updated Service Request",
            "status": ServiceRequestStatusChoices.completed.value,
        }
        response = self.client.put(
            self.get_detail_url(
                self.facility.external_id, self.service_request.external_id
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"])
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])

    def test_update_service_request_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        update_data = {
            "title": "Updated Service Request",
            "status": ServiceRequestStatusChoices.completed.value,
        }
        response = self.client.put(
            self.get_detail_url(
                self.facility.external_id, self.service_request.external_id
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        get_response = self.client.get(
            self.get_detail_url(self.facility.external_id, response.data["id"])
        )
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["title"], update_data["title"])

    def test_update_service_request_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        update_data = {
            "title": "Updated Service Request",
            "status": ServiceRequestStatusChoices.completed.value,
        }
        response = self.client.put(
            self.get_detail_url(
                self.facility.external_id, self.service_request.external_id
            ),
            update_data,
            format="json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update this service request",
            response.data["detail"],
        )

    # test cases for lisiting a service request

    def test_list_service_as_superuser(self):
        self.create_service_request(
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            title="Test Service Request 2",
        )
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_service_as_user_with_encounter_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.create_service_request(
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            title="Test Service Request 2",
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url + "?encounter=" + str(self.encounter.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_service_as_user_without_encounter_permission(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            self.url + "?encounter=" + str(self.encounter.external_id)
        )

        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to view service requests for this encounter",
            response.data["detail"],
        )

    def test_list_service_with_location_permission(self):
        self.attach_role_facility_organization_user(
            self.facility.default_internal_organization, self.user, self.role
        )
        service_request = self.create_service_request(
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            title="Test Service Request 2",
            locations=[str(self.facility_location.id)],
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url + "?location=" + str(self.facility_location.external_id)
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["id"], str(service_request.external_id)
        )

    def test_list_service_without_location_permission(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            self.url + "?location=" + str(self.facility_location.external_id)
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to view service requests for this location",
            response.data["detail"],
        )

    def test_list_service_without_location_or_encounter(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertContains(
            response, "Location or encounter is required", status_code=400
        )

    # Test cases for Apply Activity Definition

    def test_apply_activity_definition_as_superuser(self):
        activity_definition = self.create_activity_definition(
            slug="test-activity-definition",
            title="Test Activity Definition",
            description="This is a test activity definition",
        )
        self.client.force_authenticate(user=self.superuser)
        url = reverse(
            "service_request-apply-activity-definition",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        data = {
            "activity_definition": str(activity_definition.slug),
            "service_request": self.service_request_data,
            "encounter": str(self.encounter.external_id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("activity_definition", response.data)
        self.assertEqual(
            response.data["activity_definition"]["id"],
            str(activity_definition.external_id),
        )

    def test_apply_activity_definition_as_user_with_permission(self):
        activity_definition = self.create_activity_definition(
            slug="test-activity-definition",
            title="Test Activity Definition",
            description="This is a test activity definition",
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "service_request-apply-activity-definition",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        data = {
            "activity_definition": str(activity_definition.slug),
            "service_request": self.service_request_data,
            "encounter": str(self.encounter.external_id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("activity_definition", response.data)
        self.assertEqual(
            response.data["activity_definition"]["id"],
            str(activity_definition.external_id),
        )

    def test_apply_activity_definition_as_user_without_permission(self):
        activity_definition = self.create_activity_definition(
            slug="test-activity-definition",
            title="Test Activity Definition",
            description="This is a test activity definition",
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "service_request-apply-activity-definition",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        data = {
            "activity_definition": str(activity_definition.slug),
            "service_request": self.service_request_data,
            "encounter": str(self.encounter.external_id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to update this service request",
            response.data["detail"],
        )

    def test_apply_activity_definition_with_invalid_activity_definition(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "service_request-apply-activity-definition",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        data = {
            "activity_definition": "invalid-slug",  # Invalid slug
            "service_request": self.service_request_data,
            "encounter": str(self.encounter.external_id),
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertContains(
            response, "No ActivityDefinition matches the given query", status_code=404
        )

    # Test cases for create specimen

    def test_create_specimen_as_superuser(self):
        self.client.force_authenticate(user=self.superuser)
        url = reverse(
            "service_request-create-specimen",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.service_request.external_id,
            },
        )
        response = self.client.post(url, self.specimen_data, format="json")
        get_url = reverse(
            "specimen-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": response.data["id"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.data)
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_as_user_with_permission(self):
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "service_request-create-specimen",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.service_request.external_id,
            },
        )
        response = self.client.post(url, self.specimen_data, format="json")
        get_url = reverse(
            "specimen-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": response.data["id"],
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("id", response.data)
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_as_user_without_permission(self):
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "service_request-create-specimen",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.service_request.external_id,
            },
        )
        response = self.client.post(url, self.specimen_data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            "You do not have permission to create a specimen for this encounter",
            status_code=403,
        )

    # Test cases for filtering specimens

    def test_filter_service_request_by_encounter(self):
        self.client.force_authenticate(user=self.superuser)
        another_encounter = self.create_encounter(
            patient=self.patient,
            facility=self.facility,
            organization=self.facility_organization,
            current_location=self.facility_location,
        )
        self.create_service_request(
            title="Test Service Request 2",
            patient=self.patient,
            facility=self.facility,
            encounter=another_encounter,
        )
        response = self.client.get(
            self.url + "?encounter=" + str(self.encounter.external_id)
        )
        self.assertEqual(response.status_code, 200)
        response_ids = [item["encounter"]["id"] for item in response.data["results"]]
        self.assertTrue(
            all(id == str(self.encounter.external_id) for id in response_ids)
        )

    def test_filter_service_request_by_category(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_service_request(
            title="Test Service Request 2",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
        )
        response = self.client.get(
            self.url + "?category=" + ActivityDefinitionCategoryOptions.laboratory.value
        )
        self.assertEqual(response.status_code, 200)
        response_ids = [item["category"] for item in response.data["results"]]
        self.assertTrue(
            all(
                id == ActivityDefinitionCategoryOptions.laboratory.value
                for id in response_ids
            )
        )

    def test_filter_service_request_by_status(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_service_request(
            title="Test Service Request 2",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            status=ServiceRequestStatusChoices.completed.value,
        )
        response = self.client.get(
            self.url + "?status=" + ServiceRequestStatusChoices.completed.value
        )
        self.assertEqual(response.status_code, 200)
        response_ids = [item["status"] for item in response.data["results"]]
        self.assertTrue(
            all(
                id == ServiceRequestStatusChoices.completed.value for id in response_ids
            )
        )

    def test_filter_service_request_by_intent(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_service_request(
            title="Test Service Request 2",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            intent=ServiceRequestIntentChoices.order.value,
        )
        response = self.client.get(
            self.url + "?intent=" + ServiceRequestIntentChoices.order.value
        )
        self.assertEqual(response.status_code, 200)
        response_ids = [item["intent"] for item in response.data["results"]]
        self.assertTrue(
            all(id == ServiceRequestIntentChoices.order.value for id in response_ids)
        )

    def test_filter_service_request_by_priority(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_service_request(
            title="Test Service Request 2",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            priority=ServiceRequestPriorityChoices.routine.value,
        )
        response = self.client.get(
            self.url + "?priority=" + ServiceRequestPriorityChoices.routine.value
        )
        self.assertEqual(response.status_code, 200)
        response_ids = [item["priority"] for item in response.data["results"]]
        self.assertTrue(
            all(
                id == ServiceRequestPriorityChoices.routine.value for id in response_ids
            )
        )

    def test_filter_service_request_by_title(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_service_request(
            title="Test Service Request",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
        )
        response = self.client.get(self.url + "?title=Test Service Request")
        self.assertEqual(response.status_code, 200)
        response_ids = [item["title"] for item in response.data["results"]]
        self.assertTrue(all(id == "Test Service Request" for id in response_ids))

    def test_filter_service_request_by_do_not_perform(self):
        self.client.force_authenticate(user=self.superuser)
        self.create_service_request(
            title="Test Service Request",
            patient=self.patient,
            facility=self.facility,
            encounter=self.encounter,
            do_not_perform=True,
        )
        response = self.client.get(self.url + "?do_not_perform=true")
        self.assertEqual(response.status_code, 200)
        response_ids = [item["do_not_perform"] for item in response.data["results"]]
        self.assertTrue(all(id is True for id in response_ids))

    def test_create_specimen_from_definition_as_superuser(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition",
            title="Test Specimen Definition",
            description="This is a test specimen definition",
        )
        self.client.force_authenticate(user=self.superuser)
        url = reverse(
            "service_request-create-specimen-from-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.service_request.external_id,
            },
        )
        data = {
            "specimen_definition": specimen_definition.external_id,
            "specimen": self.specimen_data,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_url = reverse(
            "specimen-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": response.data["id"],
            },
        )
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_from_definition_as_user_with_permission(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition",
            title="Test Specimen Definition",
            description="This is a test specimen definition",
        )
        self.attach_role_facility_organization_user(
            self.facility_organization, self.user, self.role
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "service_request-create-specimen-from-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.service_request.external_id,
            },
        )
        data = {
            "specimen_definition": specimen_definition.external_id,
            "specimen": self.specimen_data,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 200)
        get_url = reverse(
            "specimen-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": response.data["id"],
            },
        )
        get_response = self.client.get(get_url)
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.data["id"], response.data["id"])

    def test_create_specimen_from_definition_as_user_without_permission(self):
        specimen_definition = self.create_specimen_definition(
            slug="test-specimen-definition",
            title="Test Specimen Definition",
            description="This is a test specimen definition",
        )
        self.client.force_authenticate(user=self.user)
        url = reverse(
            "service_request-create-specimen-from-definition",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "external_id": self.service_request.external_id,
            },
        )
        data = {
            "specimen_definition": specimen_definition.external_id,
            "specimen": self.specimen_data,
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertIn(
            "You do not have permission to create a specimen for this encounter",
            response.data["detail"],
        )
