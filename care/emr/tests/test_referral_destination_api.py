import uuid

from django.urls import reverse

from care.emr.models.referral import ReferralAvailability
from care.security.permissions.referral import ReferralPermissions
from care.utils.tests.base import CareAPITestBase


class ReferralDestinationAPITestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.publisher = self.create_user()
        self.facility = self.create_facility(
            user=self.publisher, name="Receiving hospital", is_public=False
        )
        self.department = self.create_facility_organization(
            facility=self.facility, name="Cardiology", org_type="dept"
        )
        self.client.force_authenticate(user=self.user)
        self.list_url = reverse("referral-availability-list")
        self.destinations_url = f"{self.list_url}destinations/"

    def make_availability(self, **kwargs):
        return ReferralAvailability.objects.create(
            **{
                "entity_type": "facility",
                "facility": self.facility,
                "name": "Specialist service",
                "status": "active",
                "is_public": True,
                "referral_type": "consultation",
                "created_by": self.publisher,
                **kwargs,
            }
        )

    def make_department_availability(self, department=None, **kwargs):
        return self.make_availability(
            entity_type="internal_organization",
            internal_organization=department or self.department,
            facility=None,
            **kwargs,
        )

    def assert_destinations(self, params, entities, *, count=None):
        response = self.client.get(self.destinations_url, params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data,
            {
                "count": len(entities) if count is None else count,
                "results": [
                    {"id": str(entity.external_id), "name": entity.name}
                    for entity in entities
                ],
            },
        )

    def test_facilities_deduplicate_units_before_search_and_pagination(self):
        # A private facility can publish public referral services without making
        # its facility record or internal department directory public.
        self.make_availability()
        for index in range(25):
            self.make_department_availability(name=f"Consultation {index}")
        same_name = self.create_facility(
            user=self.publisher, name=self.facility.name, is_public=False
        )
        self.make_availability(facility=same_name)
        last = self.create_facility(user=self.publisher, name="West clinic")
        self.make_availability(facility=last)
        hidden = self.create_facility(user=self.publisher, name="Hidden hospital")
        self.make_availability(facility=hidden, is_public=False)
        inactive = self.create_facility(user=self.publisher, name="Inactive hospital")
        self.make_availability(facility=inactive, status="inactive")
        self.make_availability(facility=inactive, status="draft")
        self.make_availability(facility=inactive, deleted=True)

        ordered = sorted(
            [self.facility, same_name, last],
            key=lambda entity: (entity.name, entity.external_id),
        )
        for offset, entity in enumerate(ordered):
            with self.subTest(offset=offset):
                self.assert_destinations(
                    {"kind": "facility", "limit": 1, "offset": offset},
                    [entity],
                    count=3,
                )
        self.assert_destinations(
            {"kind": "facility", "name": "RECEIVING", "limit": 1, "offset": 1},
            ordered[1:2],
            count=2,
        )
        self.assert_destinations({"kind": "facility", "name": "Hidden"}, [])
        self.assert_destinations({"kind": "facility", "name": "Consultation"}, [])

    def test_department_discovery_is_scoped_and_uses_availability_permissions(self):
        for _ in range(12):
            self.make_department_availability()
        permitted = self.create_facility_organization(
            facility=self.facility, name="Neurology", org_type="team"
        )
        hidden = self.create_facility_organization(
            facility=self.facility, name="Private department", org_type="dept"
        )
        inactive = self.create_facility_organization(
            facility=self.facility, name="Inactive department", org_type="dept"
        )
        self.make_department_availability(permitted, is_public=False)
        self.make_department_availability(hidden, is_public=False)
        self.make_department_availability(inactive, status="inactive")
        other = self.create_facility(user=self.publisher)
        foreign = self.create_facility_organization(facility=other, name="Foreign")
        self.make_department_availability(foreign)
        role = self.create_role_with_permissions(
            permissions=[ReferralPermissions.can_read_referral_availability.name]
        )
        self.attach_role_facility_organization_user(permitted, self.user, role)

        params = {"kind": "department", "facility": str(self.facility.external_id)}
        self.assert_destinations(params, [self.department, permitted])
        self.assert_destinations(
            {**params, "limit": 1, "offset": 1}, [permitted], count=2
        )
        self.assert_destinations({**params, "name": "NEURO"}, [permitted])
        self.assert_destinations({**params, "name": "Private"}, [])
        self.assert_destinations(
            {**params, "facility": str(other.external_id)}, [foreign]
        )

    def test_organization_discovery_deduplicates_only_readable_active_services(self):
        public = self.create_organization(name="Public referral network")
        private = self.create_organization(name="Private referral network")
        hidden = self.create_organization(name="Hidden network")
        inactive = self.create_organization(name="Inactive network")
        for organization, options in (
            (public, {}),
            (public, {}),
            (private, {"is_public": False}),
            (hidden, {"is_public": False}),
            (inactive, {"status": "inactive"}),
        ):
            self.make_availability(
                entity_type="external_organization",
                facility=None,
                external_organization=organization,
                **options,
            )
        role = self.create_role_with_permissions(
            permissions=[ReferralPermissions.can_submit_referral_availability.name]
        )
        self.attach_role_organization_user(private, self.user, role)
        self.assert_destinations({"kind": "organization"}, [private, public])
        self.assert_destinations(
            {"kind": "organization", "name": "PUBLIC", "limit": 1}, [public]
        )
        self.assert_destinations({"kind": "organization", "name": "Hidden"}, [])

    def test_facility_service_filter_uses_actual_department_not_cached_facility(self):
        direct = self.make_availability(name="Direct service")
        legacy = self.make_department_availability(name="Legacy service")
        other = self.create_facility(user=self.publisher)
        stale = self.make_department_availability(name="Legacy service")
        stale.facility = other
        stale.save(update_fields=["facility"])
        foreign = self.create_facility_organization(facility=other)
        wrong_cache = self.make_department_availability(foreign)
        wrong_cache.facility = self.facility
        wrong_cache.save(update_fields=["facility"])
        self.make_department_availability(is_public=False)
        self.make_department_availability(status="inactive")
        for scope, expected in (
            ({}, [direct, legacy, stale]),
            ({"entity_type": "facility"}, [direct]),
            ({"entity_type": "internal_organization"}, [legacy, stale]),
            ({"name": "Legacy"}, [legacy, stale]),
        ):
            with self.subTest(scope=scope):
                response = self.client.get(
                    self.list_url,
                    {"facility": str(self.facility.external_id), **scope},
                )
                self.assertEqual(response.status_code, 200, response.data)
                self.assertEqual(response.data["count"], len(expected))
                self.assertCountEqual(
                    [row["id"] for row in response.data["results"]],
                    [str(item.external_id) for item in expected],
                )
        page = self.client.get(
            self.list_url,
            {
                "facility": str(self.facility.external_id),
                "name": "Legacy",
                "ordering": "name",
                "limit": 1,
                "offset": 1,
            },
        )
        self.assertEqual(page.status_code, 200, page.data)
        self.assertEqual(page.data["count"], 2)
        self.assertEqual(
            [row["id"] for row in page.data["results"]], [str(stale.external_id)]
        )

    def test_department_only_facility_is_discovered_without_cached_facility(self):
        self.make_department_availability()
        self.assert_destinations({"kind": "facility"}, [self.facility])
        self.assert_destinations(
            {"kind": "department", "facility": str(self.facility.external_id)},
            [self.department],
        )

    def test_invalid_discovery_and_availability_scopes_are_rejected(self):
        for params in (
            {},
            {"kind": "invalid"},
            {"kind": "department"},
            {"kind": "department", "facility": "not-a-uuid"},
            {"kind": "facility", "facility": str(self.facility.external_id)},
            {"kind": "organization", "facility": str(self.facility.external_id)},
        ):
            with self.subTest(params=params):
                response = self.client.get(self.destinations_url, params)
                self.assertEqual(response.status_code, 400, response.data)
        for params in (
            {},
            {"facility": "not-a-uuid"},
            {"entity_type": "invalid", "facility": str(self.facility.external_id)},
        ):
            with self.subTest(params=params):
                response = self.client.get(self.list_url, params)
                self.assertEqual(response.status_code, 400, response.data)
        self.assert_destinations(
            {"kind": "department", "facility": str(uuid.uuid4())}, []
        )

    def test_discovery_requires_authentication_even_for_public_services(self):
        self.make_availability()
        self.client.force_authenticate(user=None)
        response = self.client.get(self.destinations_url, {"kind": "facility"})
        self.assertIn(response.status_code, (401, 403))
