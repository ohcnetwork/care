from unittest.mock import patch

from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from care.emr.fhir.resources.code_concept import MinimalCodeConcept
from care.emr.models.valueset import ValueSet
from care.utils.tests.base import CareAPITestBase


class ValueSetTestBase(CareAPITestBase):
    """
    Base class for ValueSet API tests with common setup.
    """

    def setUp(self):
        super().setUp()
        cache.clear()
        self.user = self.create_super_user()
        self.client.force_authenticate(user=self.user)
        self.valueset = baker.make(
            ValueSet,
            slug="test-valueset",
            name="Test ValueSet",
            description="A test valueset",
            status="active",
            compose={
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "123"}
                        ],
                    }
                ]
            },
            is_system_defined=False,
            created_by=self.user,
            updated_by=self.user,
        )
        self.list_url = reverse("value-set-list")
        self.detail_url = reverse(
            "value-set-detail", kwargs={"slug": self.valueset.slug}
        )

    def tearDown(self):
        cache.clear()
        super().tearDown()

    def get_detail_url(self, slug):
        return reverse("value-set-detail", kwargs={"slug": slug})

    def get_action_url(self, action_name, slug):
        return reverse(f"value-set-{action_name}", kwargs={"slug": slug})


class TestValueSetPermissionsController(ValueSetTestBase):
    """Tests for permissions_controller — read actions open to all, write only for superusers."""

    def test_list_as_superuser(self):
        """
        Test that a superuser can list value sets.
        """
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(
            response.json()["results"][0]["id"], str(self.valueset.external_id)
        )
        self.assertEqual(response.json()["results"][0]["slug"], "test-valueset")

    def test_list_as_regular_user(self):
        """
        Test that a regular user can list value sets.
        """

        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(
            response.json()["results"][0]["id"], str(self.valueset.external_id)
        )
        self.assertEqual(response.json()["results"][0]["slug"], "test-valueset")

    def test_retrieve_as_superuser(self):
        """
        Test that a superuser can retrieve a value set.
        """
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.valueset.external_id))
        self.assertEqual(response.json()["slug"], "test-valueset")

    def test_retrieve_as_regular_user(self):
        """
        Test that a regular user can retrieve a value set.
        """

        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.valueset.external_id))
        self.assertEqual(response.json()["slug"], "test-valueset")

    # Testcases for create valuesets

    def test_create_as_superuser(self):
        payload = {
            "slug": "new-valueset",
            "name": "New ValueSet",
            "description": "desc",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "456"}
                        ],
                    }
                ]
            },
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(ValueSet.objects.filter(slug="new-valueset").exists())

    def test_create_as_regular_user_denied(self):
        """
        Test that a regular user cannot create a value set.
        """
        user = self.create_user()
        self.client.force_authenticate(user=user)
        payload = {
            "slug": "blocked-valueset",
            "name": "Blocked",
            "description": "desc",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "456"}
                        ],
                    }
                ]
            },
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ValueSet.objects.filter(slug="blocked-valueset").exists())
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to perform this action.",
        )

    def test_update_as_superuser(self):
        payload = {
            "slug": "test-valueset",
            "name": "Updated Name",
            "description": "updated",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "123"}
                        ],
                    }
                ]
            },
        }
        response = self.client.put(self.detail_url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.valueset.refresh_from_db()
        self.assertEqual(self.valueset.name, "Updated Name")

    def test_update_as_regular_user_denied(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        payload = {
            "slug": "test-valueset",
            "name": "Hacked",
            "description": "hacked",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "123"}
                        ],
                    }
                ]
            },
        }
        response = self.client.put(self.detail_url, payload, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to perform this action.",
        )

    def test_delete_as_superuser(self):
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 204)

    def test_delete_as_regular_user_denied(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.json()["detail"],
            "You do not have permission to perform this action.",
        )


class TestValueSetExpand(ValueSetTestBase):
    """Tests for the expand action."""

    @patch.object(ValueSet, "search")
    def test_expand_as_superuser(self, mock_search):
        mock_result = MinimalCodeConcept(
            display="Test Code", system="http://snomed.info/sct", code="123"
        )
        mock_search.return_value = [mock_result]
        url = self.get_action_url("expand", self.valueset.slug)
        response = self.client.post(url, {"search": "test", "count": 5}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["code"], "123")
        mock_search.assert_called_once_with(
            search="test", count=5, display_language="en-gb"
        )

    @patch.object(ValueSet, "search")
    def test_expand_as_regular_user(self, mock_search):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        mock_search.return_value = []
        url = self.get_action_url("expand", self.valueset.slug)
        response = self.client.post(url, {"search": ""}, format="json")
        self.assertEqual(response.status_code, 200)

    @patch.object(ValueSet, "search")
    def test_expand_default_params(self, mock_search):
        mock_search.return_value = []
        url = self.get_action_url("expand", self.valueset.slug)
        response = self.client.post(url, {}, format="json")
        self.assertEqual(response.status_code, 200)
        mock_search.assert_called_once_with(
            search="", count=10, display_language="en-gb"
        )


class TestValueSetPreviewSearch(ValueSetTestBase):
    """Tests for the preview_search action."""

    @patch.object(ValueSet, "search")
    def test_preview_search(self, mock_search):
        mock_result = MinimalCodeConcept(
            display="Preview", system="http://snomed.info/sct", code="789"
        )
        mock_search.return_value = [mock_result]
        url = reverse("value-set-preview-search") + "?search=preview&count=5"
        payload = {
            "slug": "preview-test",
            "name": "Preview Test",
            "description": "desc",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "100"}
                        ],
                    }
                ]
            },
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["results"]), 1)
        self.assertEqual(response.json()["results"][0]["code"], "789")

    @patch.object(ValueSet, "search")
    def test_preview_search_default_params(self, mock_search):
        mock_search.return_value = []
        url = reverse("value-set-preview-search")
        payload = {
            "slug": "preview-default",
            "name": "Preview Default",
            "description": "desc",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "100"}
                        ],
                    }
                ]
            },
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

    @patch.object(ValueSet, "search")
    def test_preview_search_as_regular_user(self, mock_search):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        mock_search.return_value = []
        url = reverse("value-set-preview-search")
        payload = {
            "slug": "preview-regular",
            "name": "Preview Regular",
            "description": "desc",
            "status": "active",
            "compose": {
                "include": [
                    {
                        "system": "http://snomed.info/sct",
                        "filter": [
                            {"property": "concept", "op": "is-a", "value": "100"}
                        ],
                    }
                ]
            },
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
