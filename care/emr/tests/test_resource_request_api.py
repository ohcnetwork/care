from django.urls import reverse

from care.emr.models.resource_request import ResourceRequest, ResourceRequestComment
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
        return reverse(
            "resource-request-detail",
            kwargs={"external_id": resource_request_id},
        )

    def _get_create_data(self, **overrides):
        data = {
            "origin_facility": str(self.facility.external_id),
            "related_patient": str(self.patient.external_id),
            "title": "Resource Request",
            "status": "pending",
            "category": "other",
            "priority": 1,
            "emergency": False,
            "reason": "Test reason",
            "referring_facility_contact_name": "Contact",
            "referring_facility_contact_number": "",
        }
        data.update(overrides)
        return data

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

    def test_create_resource_request(self):
        data = self._get_create_data()
        res = self.client.post(self.base_url, data, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "Resource Request")

    def test_list_resource_requests(self):
        self.create_resource_request()
        res = self.client.get(self.base_url)
        self.assertEqual(res.status_code, 200)
        self.assertGreaterEqual(len(res.data["results"]), 1)

    def test_retrieve_resource_request(self):
        instance = self.create_resource_request()
        url = self._get_resource_request_url(instance.external_id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["id"], str(instance.external_id))

    def test_update_resource_request(self):
        instance = self.create_resource_request()
        url = self._get_resource_request_url(instance.external_id)
        data = self._get_create_data(title="Updated Title", status="approved")
        res = self.client.put(url, data, format="json")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data["title"], "Updated Title")
        self.assertEqual(res.data["status"], "approved")

    def test_delete_resource_request(self):
        instance = self.create_resource_request()
        url = self._get_resource_request_url(instance.external_id)
        res = self.client.delete(url)
        self.assertIn(res.status_code, [204, 200])

    def test_filter_by_status(self):
        self.create_resource_request(status="pending")
        self.create_resource_request(status="approved")
        res = self.client.get(self.base_url, {"status": "pending"})
        self.assertEqual(res.status_code, 200)
        for r in res.data["results"]:
            self.assertEqual(r["status"], "pending")

    def test_filter_by_origin_facility(self):
        other_facility = self.create_facility(user=self.user)
        self.create_resource_request()
        self.create_resource_request(origin_facility=other_facility)
        res = self.client.get(
            self.base_url, {"origin_facility": self.facility.external_id}
        )
        self.assertEqual(res.status_code, 200)
        for r in res.data["results"]:
            self.assertEqual(r["origin_facility"]["id"], str(self.facility.external_id))

    def test_filter_by_category(self):
        self.create_resource_request(category="other")
        self.create_resource_request(category="medicines")
        res = self.client.get(self.base_url, {"category": "other"})
        self.assertEqual(res.status_code, 200)
        for r in res.data["results"]:
            self.assertEqual(r["category"], "other")

    def test_filter_by_title(self):
        self.create_resource_request(title="Unique Title")
        self.create_resource_request(title="Other Request")
        res = self.client.get(self.base_url, {"title": "Unique"})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["results"]), 1)

    def test_assigned_to_without_assigned_facility(self):
        user2 = self.create_user()
        data = self._get_create_data(assigned_to=str(user2.external_id))
        res = self.client.post(self.base_url, data, format="json")
        self.assertContains(
            res,
            "Assigned facility is required for assigning the request to a user",
            status_code=400,
        )

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

    def test_list_resource_requests_as_superuser(self):
        self.create_resource_request(title="Request 1")
        self.create_resource_request(title="Request 2")
        other_facility = self.create_facility(user=self.user)
        self.create_resource_request(title="Request 3", origin_facility=other_facility)
        superuser = self.create_super_user()
        self.client.force_authenticate(user=superuser)
        res = self.client.get(self.base_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["results"]), 3)


class TestResourceRequestCommentViewSet(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.facility = self.create_facility(user=self.user)
        self.organization = self.create_facility_organization(facility=self.facility)
        self.patient = self.create_patient()
        self.client.force_authenticate(user=self.user)
        self.resource_request = self._create_resource_request()
        self.base_url = reverse(
            "resource-request-comment-list",
            kwargs={"resource_external_id": self.resource_request.external_id},
        )

    def _create_resource_request(self):
        return ResourceRequest.objects.create(
            origin_facility=self.facility,
            related_patient=self.patient,
            title="Test",
            status="pending",
            category="other",
            priority=1,
        )

    def _get_comment_url(self, comment_id):
        return reverse(
            "resource-request-comment-detail",
            kwargs={
                "resource_external_id": self.resource_request.external_id,
                "external_id": comment_id,
            },
        )

    def test_create_comment(self):
        res = self.client.post(
            self.base_url, {"comment": "Test comment"}, format="json"
        )
        self.assertEqual(res.status_code, 200)

    def test_list_comments(self):
        self.client.post(self.base_url, {"comment": "Comment 1"}, format="json")
        self.client.post(self.base_url, {"comment": "Comment 2"}, format="json")
        res = self.client.get(self.base_url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data["results"]), 2)

    def test_delete_comment(self):
        comment = ResourceRequestComment.objects.create(
            request=self.resource_request,
            comment="To delete",
            created_by=self.user,
        )
        url = self._get_comment_url(comment.external_id)
        res = self.client.delete(url)
        self.assertIn(res.status_code, [204, 200])
