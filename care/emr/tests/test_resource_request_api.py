from django.urls import reverse

from care.utils.tests.base import CareAPITestBase


class TestResourceRequestViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)
        self.base_url = reverse("resource-request-list")

    def _get_resource_request_url(self, resource_request_id):
        """Helper to get the detail URL for a specific resource request."""
        return reverse(
            "resource-request-detail",
            kwargs={"external_id": resource_request_id},
        )

    def create_resource_request(self, **kwargs):
        from care.emr.models.resource_request import ResourceRequest

        data = {
            "origin_facility": self.facility,
            "related_patient": self.patient,
            "title": "Resource Request",
            "status": "pending",
            "category": "other",
            "priority": 1,
        }
        data.update(kwargs)
        return ResourceRequest.objects.create(**data)

    def test_resource_request_assigned_to_user_outside_assigned_facility(self):
        assigned_to_user = self.create_user()
        assigned_facility = self.create_facility(user=assigned_to_user)
        instance = self.create_resource_request(assigned_facility=assigned_facility)
        url = self._get_resource_request_url(instance.external_id)
        data = {
            "title": instance.title,
            "status": instance.status,
            "category": instance.category,
            "emergency": instance.emergency,
            "reason": instance.reason,
            "referring_facility_contact_name": instance.referring_facility_contact_name,
            "referring_facility_contact_number": instance.referring_facility_contact_number,
            "priority": instance.priority,
            "origin_facility": instance.origin_facility.external_id,
            "assigned_facility": assigned_facility.external_id,
            "assigned_to": self.user.external_id,
        }
        res = self.client.put(url, data, "json")
        error_msg = "Assigned user is not a member of the assigned facility"
        self.assertContains(res, error_msg, status_code=400)

    def test_resource_request_assigned_to_user_within_assigned_facility(self):
        assigned_to_user = self.create_user()
        assigned_facility = self.create_facility(user=assigned_to_user)
        instance = self.create_resource_request(assigned_facility=assigned_facility)
        url = self._get_resource_request_url(instance.external_id)
        data = {
            "title": instance.title,
            "status": instance.status,
            "category": instance.category,
            "emergency": instance.emergency,
            "reason": instance.reason,
            "referring_facility_contact_name": instance.referring_facility_contact_name,
            "referring_facility_contact_number": instance.referring_facility_contact_number,
            "priority": instance.priority,
            "origin_facility": instance.origin_facility.external_id,
            "assigned_facility": assigned_facility.external_id,
            "assigned_to": assigned_to_user.external_id,
        }
        res = self.client.put(url, data, "json")
        self.assertEqual(res.status_code, 200)
