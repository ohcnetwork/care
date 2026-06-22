from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from care.emr.fhir.resources.code_concept import MinimalCodeConcept
from care.emr.models.valueset import (
    RecentViewsManager,
    UserValueSetPreference,
    ValueSet,
)
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
        mock_search.assert_called_once_with(search="", count=10)
        self.assertEqual(len(response.json()["results"]), 0)

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
        mock_search.assert_called_once_with(search="", count=10)
        self.assertEqual(len(response.json()["results"]), 0)


class TestValueSetValidateCode(ValueSetTestBase):
    """Tests for the validate_code action."""

    @patch.object(ValueSet, "lookup")
    def test_validate_code_found(self, mock_lookup):
        mock_lookup.return_value = True
        url = self.get_action_url("validate-code", self.valueset.slug)
        payload = {"code": "123", "system": "http://snomed.info/sct"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["result"])

    @patch.object(ValueSet, "lookup")
    def test_validate_code_not_found(self, mock_lookup):
        mock_lookup.return_value = False
        url = self.get_action_url("validate-code", self.valueset.slug)
        payload = {"code": "999", "system": "http://snomed.info/sct"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["result"])

    @patch.object(ValueSet, "lookup")
    def test_validate_code_as_regular_user(self, mock_lookup):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        mock_lookup.return_value = True
        url = self.get_action_url("validate-code", self.valueset.slug)
        payload = {"code": "123", "system": "http://snomed.info/sct"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)


class TestValueSetLookupCode(ValueSetTestBase):
    """Tests for the lookup_code action."""

    @patch("care.emr.api.viewsets.valueset.CodeConceptResource")
    def test_lookup_code_found(self, moke_code_concept):
        mock_resource = MagicMock()
        mock_filtered = MagicMock()
        mock_resource.filter.return_value = mock_filtered
        mock_filtered.get.return_value = {
            "code": "123",
            "system": "http://snomed.info/sct",
            "display": "Test",
        }
        moke_code_concept.return_value = mock_resource
        url = reverse("value-set-lookup-code")
        payload = {"code": "123", "system": "http://snomed.info/sct"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], "123")

    @patch("care.emr.api.viewsets.valueset.CodeConceptResource")
    def test_lookup_code_not_found(self, moke_code_concept):
        mock_resource = MagicMock()
        mock_filtered = MagicMock()
        mock_resource.filter.return_value = mock_filtered
        mock_filtered.get.side_effect = ValueError("No results found")
        moke_code_concept.return_value = mock_resource
        url = reverse("value-set-lookup-code")
        payload = {"code": "999", "system": "http://snomed.info/sct"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.json()["error"],
            "No results found for the given system and code",
        )

    @patch("care.emr.api.viewsets.valueset.CodeConceptResource")
    def test_lookup_code_as_regular_user(self, moke_code_concept):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        mock_resource = MagicMock()
        mock_filtered = MagicMock()
        mock_resource.filter.return_value = mock_filtered
        mock_filtered.get.return_value = {"code": "123"}
        moke_code_concept.return_value = mock_resource
        url = reverse("value-set-lookup-code")
        payload = {"code": "123", "system": "http://snomed.info/sct"}
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)


class TestValueSetFavourites(ValueSetTestBase):
    """Tests for favourites, add_favourite, remove_favourite, clear_favourites actions."""

    def test_favourites_empty(self):
        url = self.get_action_url("favourites", self.valueset.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_favourites_from_db_when_cache_empty(self):
        UserValueSetPreference.objects.create(
            user=self.user,
            valueset=self.valueset,
            favorite_codes=[
                {"code": "123", "display": "Test", "system": "http://snomed.info/sct"}
            ],
        )
        url = self.get_action_url("favourites", self.valueset.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["code"], "123")

    def test_favourites_from_cache(self):
        cache_key = f"user_valueset_code_prefs:{self.valueset.slug}:{self.user.external_id}:favourites"
        cached_favs = [
            {"code": "456", "display": "Cached", "system": "http://snomed.info/sct"}
        ]
        cache.set(cache_key, cached_favs)
        url = self.get_action_url("favourites", self.valueset.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["code"], "456")

    def test_favourites_as_regular_user(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("favourites", self.valueset.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch.object(ValueSet, "lookup", return_value=True)
    def test_add_favourite(self, mock_lookup):
        url = self.get_action_url("add-favourite", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test Code",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("added to favourites", response.json()["message"])
        pref = UserValueSetPreference.objects.get(
            user=self.user, valueset=self.valueset
        )
        self.assertEqual(len(pref.favorite_codes), 1)

    @patch.object(ValueSet, "lookup", return_value=True)
    def test_add_favourite_duplicate(self, mock_lookup):
        UserValueSetPreference.objects.create(
            user=self.user,
            valueset=self.valueset,
            favorite_codes=[
                {"code": "123", "display": "Test", "system": "http://snomed.info/sct"}
            ],
        )
        url = self.get_action_url("add-favourite", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test Code",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("already exists", response.json()["message"])

    @patch.object(ValueSet, "lookup", return_value=False)
    def test_add_favourite_invalid_code(self, mock_lookup):
        url = self.get_action_url("add-favourite", self.valueset.slug)
        payload = {
            "code": "invalid",
            "display": "Invalid",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)

    @patch.object(ValueSet, "lookup", return_value=True)
    def test_add_favourite_as_regular_user(self, mock_lookup):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("add-favourite", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

    def test_remove_favourite_existing(self):
        UserValueSetPreference.objects.create(
            user=self.user,
            valueset=self.valueset,
            favorite_codes=[
                {"code": "123", "display": "Test", "system": "http://snomed.info/sct"}
            ],
        )
        url = self.get_action_url("remove-favourite", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("removed from favourites", response.json()["message"])
        pref = UserValueSetPreference.objects.get(
            user=self.user, valueset=self.valueset
        )
        self.assertEqual(len(pref.favorite_codes), 0)

    def test_remove_favourite_no_preference_exists(self):
        url = self.get_action_url("remove-favourite", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("No favourites found", response.json()["message"])

    def test_remove_favourite_as_regular_user(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("remove-favourite", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

    def test_clear_favourites_existing(self):
        UserValueSetPreference.objects.create(
            user=self.user,
            valueset=self.valueset,
            favorite_codes=[
                {"code": "123", "display": "Test", "system": "http://snomed.info/sct"}
            ],
        )
        url = self.get_action_url("clear-favourites", self.valueset.slug)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("All favourites cleared", response.json()["message"])
        pref = UserValueSetPreference.objects.get(
            user=self.user, valueset=self.valueset
        )
        self.assertEqual(pref.favorite_codes, [])

    def test_clear_favourites_no_preference_exists(self):
        url = self.get_action_url("clear-favourites", self.valueset.slug)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("No favourites found", response.json()["message"])

    def test_clear_favourites_as_regular_user(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("clear-favourites", self.valueset.slug)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)


class TestValueSetRecentViews(ValueSetTestBase):
    @patch.object(ValueSet, "lookup", return_value=True)
    def test_add_recent_view(self, mock_lookup):
        url = self.get_action_url("add-recent-view", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("added to recent views", response.json()["message"])

    @patch.object(ValueSet, "lookup", return_value=False)
    def test_add_recent_view_invalid_code(self, mock_lookup):
        url = self.get_action_url("add-recent-view", self.valueset.slug)
        payload = {
            "code": "invalid",
            "display": "Invalid",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid code value", str(response.json()))

    @patch.object(ValueSet, "lookup", return_value=True)
    def test_add_recent_view_as_regular_user(self, mock_lookup):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("add-recent-view", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

    def test_remove_recent_view(self):
        url = self.get_action_url("remove-recent-view", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("removed from recent views", response.json()["message"])

    def test_remove_recent_view_as_regular_user(self):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("remove-recent-view", self.valueset.slug)
        payload = {
            "code": "123",
            "display": "Test",
            "system": "http://snomed.info/sct",
        }
        response = self.client.post(url, payload, format="json")
        self.assertEqual(response.status_code, 200)

    @patch.object(RecentViewsManager, "get_recent_views", return_value=[])
    def test_recent_views_empty(self, mock_get):
        url = self.get_action_url("recent-views", self.valueset.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    @patch.object(
        RecentViewsManager,
        "get_recent_views",
        return_value=[
            {"code": "123", "display": "Test", "system": "http://snomed.info/sct"}
        ],
    )
    def test_recent_views_with_data(self, mock_get):
        url = self.get_action_url("recent-views", self.valueset.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["code"], "123")

    @patch.object(RecentViewsManager, "get_recent_views", return_value=[])
    def test_recent_views_as_regular_user(self, mock_get):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("recent-views", self.valueset.slug)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    @patch.object(RecentViewsManager, "clear_recent_views")
    def test_clear_recent_views(self, mock_clear):
        url = self.get_action_url("clear-recent-views", self.valueset.slug)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("All recent views cleared", response.json()["message"])
        mock_clear.assert_called_once()

    @patch.object(RecentViewsManager, "clear_recent_views")
    def test_clear_recent_views_as_regular_user(self, mock_clear):
        user = self.create_user()
        self.client.force_authenticate(user=user)
        url = self.get_action_url("clear-recent-views", self.valueset.slug)
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
