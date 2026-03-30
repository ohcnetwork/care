from django.core.cache import cache
from django.urls import reverse
from model_bakery import baker

from care.emr.models.valueset import (
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
