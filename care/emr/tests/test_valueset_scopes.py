from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse

from care.emr.api.viewsets.valueset import get_closest_valueset
from care.emr.models.valueset import (
    RecentViewsManager,
    UserFacilityValueSetPreference,
    UserValueSetPreference,
    ValueSet,
    ValueSetFacilityOrganization,
)
from care.security.permissions.valueset import ValueSetPermissions
from care.utils.tests.base import CareAPITestBase


class ScopedValueSetTests(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.admin = self.create_super_user()
        self.user = self.create_user()
        self.facility = self.create_facility(self.admin, name="Test Clinic")
        self.root_org = self.create_facility_organization(
            self.facility, org_type="root"
        )
        self.department = self.create_facility_organization(
            self.facility, org_type="dept", parent=self.root_org
        )
        self.client.force_authenticate(self.admin)
        self.instance = self.valueset()
        self.facility_valueset = self.valueset(
            auth_context="facility", facility=self.facility
        )
        self.personal = self.valueset(
            auth_context="user", facility=self.facility, created_by=self.user
        )

    def valueset(self, **kwargs):
        return ValueSet.objects.create(
            **{
                "slug": "vital-signs",
                "name": "Vital signs",
                "description": "Clinical observations",
                "compose": {"include": [], "exclude": []},
                "status": "active",
                "auth_context": "instance",
                "created_by": self.admin,
                **kwargs,
            }
        )

    def payload(self, **kwargs):
        return {
            "slug": "local-vital-signs",
            "name": "Local vital signs",
            "description": "Facility codes",
            "compose": {"include": [], "exclude": []},
            "status": "active",
            "disable_composition": False,
            "auth_context": "facility",
            "facility": str(self.facility.external_id),
            "inherited": False,
            **kwargs,
        }

    def action_url(self, valueset, action):
        return reverse(
            f"value-set-{action}", kwargs={"external_id": valueset.external_id}
        )

    def prefer(self, valueset, *, user=None):
        return UserFacilityValueSetPreference.objects.create(
            user=user or self.user,
            facility=self.facility,
            slug=self.instance.slug,
            valueset=valueset,
        )

    def test_slug_resolution_prefers_facility_then_instance(self):
        queryset = ValueSet.objects.all()
        self.assertEqual(
            get_closest_valueset(queryset, self.instance.slug, self.user),
            self.instance,
        )
        self.assertEqual(
            get_closest_valueset(
                queryset, self.instance.slug, self.user, self.facility.external_id
            ),
            self.facility_valueset,
        )
        other_facility = self.create_facility(self.admin)
        self.assertEqual(
            get_closest_valueset(
                queryset, self.instance.slug, self.user, other_facility.external_id
            ),
            self.instance,
        )

    def test_slug_preference_is_user_specific(self):
        self.prefer(self.personal)
        queryset = ValueSet.objects.all()
        self.assertEqual(
            get_closest_valueset(
                queryset, self.instance.slug, self.user, self.facility.external_id
            ),
            self.personal,
        )
        self.assertEqual(
            get_closest_valueset(
                queryset, self.instance.slug, self.admin, self.facility.external_id
            ),
            self.facility_valueset,
        )

    def test_slug_resolution_ignores_inaccessible_preference(self):
        self.prefer(self.personal)
        queryset = ValueSet.objects.exclude(pk=self.personal.pk)
        self.assertEqual(
            get_closest_valueset(
                queryset, self.instance.slug, self.user, self.facility.external_id
            ),
            self.facility_valueset,
        )

    def test_expand_slug_returns_selected_valueset_and_passes_search_parameters(self):
        self.prefer(self.personal, user=self.admin)
        with patch.object(ValueSet, "search", return_value=[]) as search:
            response = self.client.post(
                reverse("value-set-expand-slug"),
                {
                    "slug": self.instance.slug,
                    "facility": str(self.facility.external_id),
                    "search": "pulse",
                    "count": 7,
                    "display_language": "hi",
                },
                format="json",
            )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(
            response.data["valueset"]["id"], str(self.personal.external_id)
        )
        self.assertEqual(response.data["results"], [])
        search.assert_called_once_with(search="pulse", count=7, display_language="hi")

    def test_expand_slug_missing_valueset_is_a_validation_error(self):
        response = self.client.post(
            reverse("value-set-expand-slug"), {"slug": "missing"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No valueset found", str(response.data))

    def test_setting_slug_preference_replaces_the_existing_selection(self):
        payload = {
            "slug": self.instance.slug,
            "facility": str(self.facility.external_id),
        }
        for valueset in (self.instance, self.facility_valueset):
            response = self.client.post(
                self.action_url(valueset, "set-slug-preference"), payload, format="json"
            )
            self.assertEqual(response.status_code, 200, response.data)
        preference = UserFacilityValueSetPreference.objects.get(
            user=self.admin, facility=self.facility, slug=self.instance.slug
        )
        self.assertEqual(preference.valueset, self.facility_valueset)

    def test_cross_facility_slug_preference_is_rejected(self):
        other_facility = self.create_facility(self.admin)
        response = self.client.post(
            self.action_url(self.facility_valueset, "set-slug-preference"),
            {"slug": self.instance.slug, "facility": str(other_facility.external_id)},
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(UserFacilityValueSetPreference.objects.exists())

    def test_favourites_by_slug_use_the_selected_valueset(self):
        codes = [
            {"code": "pulse", "system": "http://example.org/codes", "display": "Pulse"}
        ]
        UserValueSetPreference.objects.create(
            user=self.admin, valueset=self.facility_valueset, favorite_codes=codes
        )
        response = self.client.get(
            reverse("value-set-favourites-by-slug"),
            {"slug": self.instance.slug, "facility": str(self.facility.external_id)},
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, codes)

    def test_recent_views_by_slug_use_the_selected_valueset_cache(self):
        with patch.object(
            RecentViewsManager, "get_recent_views", return_value=[]
        ) as recent_views:
            response = self.client.get(
                reverse("value-set-recent-views-by-slug"),
                {
                    "slug": self.instance.slug,
                    "facility": str(self.facility.external_id),
                },
            )
        self.assertEqual(response.status_code, 200, response.data)
        recent_views.assert_called_once_with(
            f"user_valueset_code_prefs:{self.facility_valueset.external_id}:{self.admin.external_id}:recent_views"
        )

    def test_create_inherited_valueset_uses_parent_slug_and_preserves_it_on_update(
        self,
    ):
        response = self.client.post(
            reverse("value-set-list"),
            self.payload(
                slug="ignored-child-slug",
                inherited=True,
                parent=str(self.instance.external_id),
                auth_context="user",
            ),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        child = ValueSet.objects.get(external_id=response.data["id"])
        self.assertEqual(child.slug, self.instance.slug)
        self.assertEqual(child.parent, self.instance)
        response = self.client.put(
            self.action_url(child, "detail"),
            self.payload(slug="changed-slug"),
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        child.refresh_from_db()
        self.assertEqual(child.slug, self.instance.slug)

    def test_inheritance_requires_parent(self):
        response = self.client.post(
            reverse("value-set-list"), self.payload(inherited=True), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Parent is required", str(response.data))

    def test_cross_facility_parent_is_rejected(self):
        parent = self.valueset(
            auth_context="facility", facility=self.create_facility(self.admin)
        )
        response = self.client.post(
            reverse("value-set-list"),
            self.payload(inherited=True, parent=str(parent.external_id)),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Parent not found", str(response.data))

    def test_reserved_slug_is_rejected_for_noninherited_valueset(self):
        response = self.client.post(
            reverse("value-set-list"), self.payload(slug="system-local"), format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_facility_organization_assignment_updates_access_cache(self):
        url = self.action_url(self.facility_valueset, "set-facility-organizations")
        response = self.client.post(
            url,
            {"facility_organizations": [str(self.department.external_id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.facility_valueset.refresh_from_db()
        self.assertCountEqual(
            self.facility_valueset.internal_organization_cache,
            [self.root_org.id, self.department.id],
        )
        role = self.create_role_with_permissions(
            [ValueSetPermissions.can_read_valueset.name]
        )
        self.attach_role_facility_organization_user(self.department, self.user, role)
        self.client.force_authenticate(self.user)
        response = self.client.get(self.action_url(self.facility_valueset, "detail"))
        self.assertEqual(response.status_code, 200, response.data)

    def test_cross_facility_organization_assignment_rolls_back(self):
        ValueSetFacilityOrganization.objects.create(
            valueset=self.facility_valueset, organization=self.department
        )
        other_org = self.create_facility_organization(
            self.create_facility(self.admin), org_type="root"
        )
        response = self.client.post(
            self.action_url(self.facility_valueset, "set-facility-organizations"),
            {"facility_organizations": [str(other_org.external_id)]},
            format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            ValueSetFacilityOrganization.objects.get(
                valueset=self.facility_valueset
            ).organization,
            self.department,
        )

    def test_facility_organization_endpoints_list_replace_and_clear_assignments(self):
        set_url = self.action_url(self.facility_valueset, "set-facility-organizations")
        get_url = self.action_url(self.facility_valueset, "get-facility-organizations")
        for organization in (self.department, self.root_org):
            response = self.client.post(
                set_url,
                {"facility_organizations": [str(organization.external_id)]},
                format="json",
            )
            self.assertEqual(response.status_code, 200, response.data)
            listed = self.client.get(get_url)
            self.assertEqual(listed.status_code, 200, listed.data)
            self.assertEqual(listed.data["count"], 1)
            self.assertEqual(
                listed.data["results"][0]["id"], str(organization.external_id)
            )
            self.facility_valueset.refresh_from_db()
            self.assertCountEqual(
                self.facility_valueset.internal_organization_cache,
                [*organization.parent_cache, organization.pk],
            )

        response = self.client.post(
            set_url, {"facility_organizations": []}, format="json"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.facility_valueset.refresh_from_db()
        self.assertEqual(self.facility_valueset.internal_organization_cache, [])
        self.assertFalse(
            ValueSetFacilityOrganization.objects.filter(
                valueset=self.facility_valueset
            ).exists()
        )
        self.assertEqual(self.client.get(get_url).data["count"], 0)

    def test_facility_organization_endpoints_reject_other_valueset_scopes(self):
        for valueset in (self.instance, self.personal):
            with self.subTest(context=valueset.auth_context):
                listed = self.client.get(
                    self.action_url(valueset, "get-facility-organizations")
                )
                self.assertEqual(listed.status_code, 403, listed.data)
                assigned = self.client.post(
                    self.action_url(valueset, "set-facility-organizations"),
                    {"facility_organizations": [str(self.department.external_id)]},
                    format="json",
                )
                self.assertEqual(assigned.status_code, 403, assigned.data)
        self.assertFalse(ValueSetFacilityOrganization.objects.exists())

    def test_user_valuesets_are_only_visible_to_their_creator(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("value-set-list"))
        self.assertEqual(response.status_code, 200)
        self.assertCountEqual(
            [obj["id"] for obj in response.data["results"]],
            [str(self.instance.external_id), str(self.personal.external_id)],
        )
        self.assertEqual(
            self.client.get(
                self.action_url(self.facility_valueset, "detail")
            ).status_code,
            404,
        )

    def test_personal_valueset_creator_requires_write_permission_to_update(self):
        self.client.force_authenticate(self.user)
        url = self.action_url(self.personal, "detail")
        response = self.client.put(url, self.payload(name="Updated"), format="json")
        self.assertEqual(response.status_code, 403)
        role = self.create_role_with_permissions(
            [ValueSetPermissions.can_write_valueset.name]
        )
        self.attach_role_facility_organization_user(self.root_org, self.user, role)
        response = self.client.put(url, self.payload(name="Updated"), format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.personal.refresh_from_db()
        self.assertEqual(self.personal.name, "Updated")

    def test_composition_inherits_parent_and_can_be_disabled(self):
        self.instance.compose = {
            "include": [
                {"system": "http://example.org/parent", "concept": [{"code": "parent"}]}
            ],
            "exclude": [],
        }
        self.instance.save(update_fields=["compose"])
        self.personal.parent = self.instance
        self.personal.compose = {
            "include": [
                {"system": "http://example.org/child", "concept": [{"code": "child"}]}
            ],
            "exclude": [],
        }
        self.personal.save()
        self.assertEqual(
            set(self.personal.create_composition()),
            {"http://example.org/parent", "http://example.org/child"},
        )
        self.personal.disable_composition = True
        self.assertEqual(
            set(self.personal.create_composition()), {"http://example.org/child"}
        )

    def test_facility_writer_can_create_a_valueset_in_their_own_facility(self):
        role = self.create_role_with_permissions(
            [ValueSetPermissions.can_write_valueset.name]
        )
        self.attach_role_facility_organization_user(self.root_org, self.user, role)
        self.client.force_authenticate(self.user)

        response = self.client.post(
            reverse("value-set-list"), self.payload(), format="json"
        )

        self.assertEqual(response.status_code, 200, response.data)
        created = ValueSet.objects.get(external_id=response.data["id"])
        self.assertEqual(created.facility, self.facility)
        self.assertEqual(created.created_by, self.user)

    def test_facility_valueset_creation_requires_a_write_role_at_the_same_facility_root(
        self,
    ):
        other_facility = self.create_facility(self.admin)
        other_root = self.create_facility_organization(other_facility, org_type="root")
        for organization, permission in (
            (other_root, ValueSetPermissions.can_write_valueset.name),
            (self.department, ValueSetPermissions.can_write_valueset.name),
            (self.root_org, ValueSetPermissions.can_read_valueset.name),
        ):
            with self.subTest(organization=organization.pk, permission=permission):
                user = self.create_user()
                role = self.create_role_with_permissions([permission])
                self.attach_role_facility_organization_user(organization, user, role)
                self.client.force_authenticate(user)
                response = self.client.post(
                    reverse("value-set-list"), self.payload(), format="json"
                )
                self.assertEqual(response.status_code, 403, response.data)
                self.assertFalse(
                    ValueSet.objects.filter(slug="local-vital-signs").exists()
                )

    def test_composition_preserves_exclusions_from_an_included_code_system(self):
        system = "http://example.org/codes"
        include = {"system": system, "concept": [{"code": "included"}]}
        exclude = {"system": system, "concept": [{"code": "excluded"}]}
        self.instance.compose = {"include": [include], "exclude": [exclude]}

        self.assertEqual(
            self.instance.create_composition(),
            {system: {"include": [include], "exclude": [exclude]}},
        )


class ValueSetCompositionTests(SimpleTestCase):
    system = "http://example.org/codes"

    def concept(self, code):
        return {"system": self.system, "concept": [{"code": code}]}

    def test_inherited_same_system_composition_preserves_child_then_parent_order(self):
        grandparent_include = self.concept("grandparent-include")
        grandparent_exclude = self.concept("grandparent-exclude")
        parent_include = self.concept("parent-include")
        parent_exclude = self.concept("parent-exclude")
        child_include = self.concept("child-include")
        child_exclude = self.concept("child-exclude")
        grandparent = ValueSet(
            compose={"include": [grandparent_include], "exclude": [grandparent_exclude]}
        )
        parent = ValueSet(
            parent=grandparent,
            compose={"include": [parent_include], "exclude": [parent_exclude]},
        )
        child = ValueSet(
            parent=parent,
            compose={"include": [child_include], "exclude": [child_exclude]},
        )
        self.assertEqual(
            child.create_composition(),
            {
                self.system: {
                    "include": [child_include, parent_include, grandparent_include],
                    "exclude": [child_exclude, parent_exclude, grandparent_exclude],
                }
            },
        )
        parent.disable_composition = True
        self.assertEqual(
            child.create_composition(),
            {
                self.system: {
                    "include": [child_include, parent_include],
                    "exclude": [child_exclude, parent_exclude],
                }
            },
        )
        child.disable_composition = True
        self.assertEqual(
            child.create_composition(),
            {self.system: {"include": [child_include], "exclude": [child_exclude]}},
        )

    def test_child_exclusion_and_parent_inclusion_of_the_same_system_are_preserved(
        self,
    ):
        include = self.concept("parent-include")
        exclude = self.concept("child-exclude")
        parent = ValueSet(compose={"include": [include], "exclude": []})
        child = ValueSet(parent=parent, compose={"include": [], "exclude": [exclude]})
        self.assertEqual(
            child.create_composition(),
            {self.system: {"include": [include], "exclude": [exclude]}},
        )

    def test_composition_accepts_omitted_optional_exclusions(self):
        include = self.concept("included")
        valueset = ValueSet(compose={"include": [include]})
        self.assertEqual(
            valueset.create_composition(), {self.system: {"include": [include]}}
        )
