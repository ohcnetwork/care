from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse

from care.emr.api.viewsets.charge_item_definition import ChargeItemDefinitionViewSet
from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.favorites import (
    UserResourceFavorites,
    favorite_list_object_cache_key,
    favorite_lists_cache_key,
)
from care.emr.resources.charge_item_definition.spec import (
    ChargeItemDefinitionStatusOptions,
)
from care.emr.resources.favorites.spec import DEFAULT_FAVORITE_LIST
from care.utils.tests.base import CareAPITestBase


class TestFavorites(CareAPITestBase):
    def tearDown(self):
        cache.delete(self.favorite_list_cache_key)
        cache.delete(self.favorite_list_object_cache_key)
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.user = self.create_super_user()
        self.facility = self.create_facility(user=self.user)

        self.favorite_list_name = DEFAULT_FAVORITE_LIST
        self.FAVORITE_RESOURCE = ChargeItemDefinitionViewSet.FAVORITE_RESOURCE

        self.base_url = reverse(
            "charge_item_definition-list",
            kwargs={"facility_external_id": self.facility.external_id},
        )
        self.favorite_list_cache_key = favorite_lists_cache_key(
            self.user, self.FAVORITE_RESOURCE, self.facility
        )
        self.favorite_list_object_cache_key = favorite_list_object_cache_key(
            self.user,
            self.FAVORITE_RESOURCE,
            self.facility,
            self.favorite_list_name,
        )
        self.list_queryset = UserResourceFavorites.objects.filter(
            user=self.user,
            favorite_list=self.favorite_list_name,
            resource_type=self.FAVORITE_RESOURCE,
            facility=self.facility,
        )
        cache.delete(self.favorite_list_cache_key)
        cache.delete(self.favorite_list_object_cache_key)
        self.client.force_authenticate(user=self.user)

    def _get_detail_url(self, slug):
        return reverse(
            "charge_item_definition-detail",
            kwargs={
                "facility_external_id": self.facility.external_id,
                "slug": slug,
            },
        )

    def create_charge_item_definition(self, **kwargs):
        data = {
            "facility": self.facility,
            "status": ChargeItemDefinitionStatusOptions.active.value,
            "title": self.fake.sentence(nb_words=4),
            "slug": f"f-{self.facility.external_id}-{self.fake.slug()}",
            "description": self.fake.text(),
        }
        data.update(**kwargs)
        return ChargeItemDefinition.objects.create(**data)

    def test_add_favorite(self):
        charge_item = self.create_charge_item_definition()
        response = self.client.post(
            self._get_detail_url(charge_item.slug) + "add_favorite/",
        )

        self.assertEqual(response.status_code, 200, response.content)
        favorite_list_obj = self.list_queryset.first()
        self.assertEqual(
            favorite_list_obj.favorites,
            [charge_item.id],
            "Favorite list should contain the added charge item",
        )
        data = cache.get(self.favorite_list_object_cache_key)
        self.assertEqual(
            data, [charge_item.id], "Cache should contain the added charge item"
        )

        charge_item_2 = self.create_charge_item_definition()
        charge_item_3 = self.create_charge_item_definition()
        self.client.post(
            self._get_detail_url(charge_item_3.slug) + "add_favorite/",
        )
        self.client.post(
            self._get_detail_url(charge_item_2.slug) + "add_favorite/",
        )
        expected_list = [charge_item_2.id, charge_item_3.id, charge_item.id]
        favorite_list_obj.refresh_from_db()
        self.assertEqual(
            favorite_list_obj.favorites,
            expected_list,
            "Order of favorites should be maintained",
        )

        data = cache.get(self.favorite_list_object_cache_key)
        self.assertEqual(data, expected_list)

    @override_settings(MAX_FAVORITES_PER_LIST=3)
    def test_favorites_truncated_to_max_limit(self):
        UserResourceFavorites.objects.create(
            user=self.user,
            favorite_list=self.favorite_list_name,
            resource_type=self.FAVORITE_RESOURCE,
            facility=self.facility,
            favorites=[
                1000001,
                1000002,
                1000003,
            ],
        )

        charge_item = self.create_charge_item_definition()
        response = self.client.post(
            self._get_detail_url(charge_item.slug) + "add_favorite/",
        )
        self.assertEqual(response.status_code, 200, response.content)
        favorite_list_obj = self.list_queryset.first()
        self.assertEqual(
            favorite_list_obj.favorites,
            [charge_item.id, 1000001, 1000002],
            "Favorite list should contain the added charge item and be truncated to max limit",
        )

    def test_remove_favorite_single(self):
        charge_item = self.create_charge_item_definition()
        charge_item_2 = self.create_charge_item_definition()
        UserResourceFavorites.objects.create(
            user=self.user,
            favorite_list=self.favorite_list_name,
            resource_type=self.FAVORITE_RESOURCE,
            facility=self.facility,
            favorites=[
                charge_item_2.id,
                charge_item.id,
            ],
        )

        data = cache.get(self.favorite_list_object_cache_key)
        self.assertEqual(
            data,
            [charge_item_2.id, charge_item.id],
            "Cache should contain both items before deletion",
        )

        response = self.client.post(
            self._get_detail_url(charge_item_2.slug) + "remove_favorite/",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            self.list_queryset.first().favorites,
            [charge_item.id],
            "Favorite list should contain only the remaining charge item",
        )
        data = cache.get(self.favorite_list_object_cache_key)
        self.assertEqual(
            data, [charge_item.id], "Cache should contain only the remaining item"
        )

        response = self.client.post(
            self._get_detail_url(charge_item.slug) + "remove_favorite/",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(
            self.list_queryset.first(), "Favorite list should be deleted when empty"
        )
        null = object()
        data = cache.get(self.favorite_list_object_cache_key, null)
        self.assertEqual(
            data, null, "Cache should be cleared when favorite list is deleted"
        )

    def test_delete_favorite_from_non_existent_list(self):
        charge_item = self.create_charge_item_definition()
        response = self.client.post(
            self._get_detail_url(charge_item.slug) + "remove_favorite/",
            data={"favorite_list": "non_existent_list"},
            format="json",
        )
        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn("Favorite List not found", str(response.data))

    def test_list_favorites_list(self):
        charge_item = self.create_charge_item_definition()
        charge_item_2 = self.create_charge_item_definition()
        charge_item_3 = self.create_charge_item_definition()

        self.client.post(
            self._get_detail_url(charge_item.slug) + "add_favorite/",
            data={"favorite_list": self.favorite_list_name},
            format="json",
        )
        self.client.post(
            self._get_detail_url(charge_item_3.slug) + "add_favorite/",
            data={"favorite_list": self.favorite_list_name},
            format="json",
        )
        self.client.post(
            self._get_detail_url(charge_item_2.slug) + "add_favorite/",
            data={"favorite_list": "another_list"},
            format="json",
        )

        response = self.client.get(
            self.base_url + "favorite_lists/",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(
            set(response.data["lists"]),
            {self.favorite_list_name, "another_list"},
            "Response should contain both favorite lists",
        )
        data = cache.get(self.favorite_list_cache_key)
        self.assertEqual(
            set(data),
            {self.favorite_list_name, "another_list"},
            "Cache should contain both favorite lists",
        )
        cache.delete(
            favorite_list_object_cache_key(
                self.user,
                self.FAVORITE_RESOURCE,
                self.facility,
                "another_list",
            )
        )

    def test_list_ordered_by_favorites(self):
        charge_item = self.create_charge_item_definition()
        charge_item_2 = self.create_charge_item_definition()
        charge_item_3 = self.create_charge_item_definition()
        charge_item_4 = self.create_charge_item_definition()

        UserResourceFavorites.objects.create(
            user=self.user,
            favorite_list=self.favorite_list_name,
            resource_type=self.FAVORITE_RESOURCE,
            facility=self.facility,
            favorites=[
                charge_item_4.id,
                charge_item_2.id,
                charge_item.id,
                charge_item_3.id,
            ],
        )

        response = self.client.get(
            self.base_url + f"?favorite_list={self.favorite_list_name}",
        )
        self.assertEqual(response.status_code, 200, response.content)
        response_ids = [item["id"] for item in response.data["results"]]
        self.assertEqual(
            response_ids,
            [
                str(charge_item_4.external_id),
                str(charge_item_2.external_id),
                str(charge_item.external_id),
                str(charge_item_3.external_id),
            ],
            "Response should be ordered as per the favorite list",
        )
