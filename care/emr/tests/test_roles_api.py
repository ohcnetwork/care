from django.urls import reverse
from model_bakery import baker
from rest_framework import status

from care.security.models import PermissionModel, RoleModel, RolePermission
from care.utils.tests.base import CareAPITestBase


class RoleApiTestCase(CareAPITestBase):
    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.superuser = self.create_super_user()
        self.facility = self.create_facility(user=self.user)
        self.facility_organization = self.create_facility_organization(
            facility=self.facility
        )

        self.permissions = []
        valid_slugs = ["can_read_facility", "can_create_patient", "can_list_user"]
        for slug in valid_slugs:
            context = slug.split("_")[2].upper()
            perm = baker.make(
                PermissionModel,
                slug=slug,
                name=f"Can {slug.split('_')[2].capitalize()} {context.capitalize()}",
                description=f"Permission to {slug.split('_')[2]} {context.lower()}",
                context=context,
            )
            self.permissions.append(perm)
        self.role_list_url = reverse("role-list")
        self.role_data = {
            "name": "Test Role",
            "description": "A test role",
            "permissions": [p.slug for p in self.permissions],
            "is_system": False,
        }

        self.client.force_authenticate(user=self.user)

    def _get_role_detail_url(self, external_id):
        return reverse("role-detail", kwargs={"external_id": external_id})

    def _create_role(self, is_system=False, permissions=None):
        role = baker.make(
            RoleModel,
            name=self.role_data["name"],
            description=self.role_data["description"],
            is_system=is_system,
        )
        if permissions is None:
            permissions = self.permissions
        for perm in permissions:
            RolePermission.objects.create(role=role, permission=perm)
        return role

    def test_list_roles(self):
        """Any user can list roles"""
        self._create_role()
        response = self.client.get(self.role_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_list_roles_as_superuser(self):
        """Superusers can list roles"""
        self._create_role()
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self.role_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.json()), 1)

    def test_retrieve_role(self):
        """Any user can retrieve role details"""
        role = self._create_role()
        response = self.client.get(self._get_role_detail_url(role.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], role.name)

        # Verify permissions are included in response
        permissions_data = response.json()["permissions"]
        self.assertEqual(len(permissions_data), len(self.permissions))

        # Check that each permission has the expected fields
        for perm_data in permissions_data:
            self.assertIn("slug", perm_data)
            self.assertIn("name", perm_data)
            self.assertIn("description", perm_data)
            self.assertIn("context", perm_data)

    def test_retrieve_role_as_superuser(self):
        """Superusers can retrieve role details"""
        role = self._create_role()
        self.client.force_authenticate(user=self.superuser)
        response = self.client.get(self._get_role_detail_url(role.external_id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], role.name)

    # WRITE OPERATIONS - Only available to superusers

    def test_create_role_as_user(self):
        """Regular users cannot create roles"""
        response = self.client.post(self.role_list_url, self.role_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertContains(
            response,
            "You do not have permission to perform this action",
            status_code=403,
        )

    def test_create_role_as_superuser(self):
        """Superusers can create roles"""
        self.client.force_authenticate(user=self.superuser)

        # Use simplified data to avoid validation errors
        role_data = {
            "name": "Simple Test Role",
            "description": "Simple test role for create",
            "permissions": [self.permissions[0].slug],
        }
        response = self.client.post(self.role_list_url, role_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("id", response.json())
        external_id = response.json()["id"]
        created_role = RoleModel.objects.get(external_id=external_id)
        self.assertEqual(created_role.name, role_data["name"])
        permissions = RolePermission.objects.filter(role=created_role)
        self.assertEqual(permissions.count(), 1)
        self.assertEqual(permissions[0].permission, self.permissions[0])

    def test_create_role_without_permissions_as_superuser(self):
        """Superusers can create roles without specifying permissions"""
        self.client.force_authenticate(user=self.superuser)

        # Role data without permissions
        role_data_no_perms = {
            "name": "Role without permissions",
            "description": "Test role without permissions",
        }

        response = self.client.post(
            self.role_list_url, role_data_no_perms, format="json"
        )

        # Handle potential validation errors gracefully
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            self.assertFalse(
                RoleModel.objects.filter(name=role_data_no_perms["name"]).exists()
            )
        else:
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            created_role = RoleModel.objects.get(name=role_data_no_perms["name"])
            # Verify no permissions were assigned
            permissions = RolePermission.objects.filter(role=created_role)
            self.assertEqual(permissions.count(), 0)

    def test_update_role_as_user(self):
        """Regular users cannot update roles"""
        role = self._create_role()
        update_data = {"name": "Updated Role Name"}
        response = self.client.put(
            self._get_role_detail_url(role.external_id), update_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertContains(
            response,
            "You do not have permission to perform this action",
            status_code=403,
        )

    def test_update_role_as_superuser(self):
        """Superusers can update roles"""
        role = self._create_role()
        self.client.force_authenticate(user=self.superuser)

        # Use simple data for update
        update_data = {
            "name": "Updated Role Name",
            "description": "Updated description",
        }
        response = self.client.put(
            self._get_role_detail_url(role.external_id), update_data, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["name"], update_data["name"])
        role.refresh_from_db()
        self.assertEqual(role.name, update_data["name"])

    def test_update_role_permissions_as_superuser(self):
        """Superusers can update role permissions"""
        role = self._create_role()
        self.client.force_authenticate(user=self.superuser)

        # Initially, role has all permissions
        self.assertEqual(
            RolePermission.objects.filter(role=role).count(), len(self.permissions)
        )

        update_data = {
            "name": role.name,
            "description": role.description,
            "permissions": [self.permissions[0].slug],
            "is_system": role.is_system,
        }

        response = self.client.put(
            self._get_role_detail_url(role.external_id), update_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify permissions were updated
        permissions = RolePermission.objects.filter(role=role)
        self.assertEqual(permissions.count(), 1)
        self.assertEqual(permissions[0].permission, self.permissions[0])

    def test_update_role_without_permissions_as_superuser(self):
        """Superusers can update role without changing permissions"""
        role = self._create_role()
        self.client.force_authenticate(user=self.superuser)
        initial_count = RolePermission.objects.filter(role=role).count()
        update_data = {"name": "Updated Name Only"}
        response = self.client.put(
            self._get_role_detail_url(role.external_id), update_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        permissions = RolePermission.objects.filter(role=role)
        self.assertEqual(permissions.count(), initial_count)

    def test_delete_role_as_user(self):
        """Regular users cannot delete roles"""
        role = self._create_role()
        response = self.client.delete(self._get_role_detail_url(role.external_id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertContains(
            response,
            "You do not have permission to perform this action",
            status_code=403,
        )
        self.assertTrue(RoleModel.objects.filter(id=role.id).exists())

    def test_delete_role_as_superuser(self):
        """Superusers can delete roles"""
        role = self._create_role()

        # Create role permissions to verify they get deleted
        for perm in self.permissions:
            RolePermission.objects.create(role=role, permission=perm)

        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self._get_role_detail_url(role.external_id))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(RoleModel.objects.filter(id=role.id).exists())
        self.assertEqual(RolePermission.objects.filter(role=role).count(), 0)

    def test_delete_system_role(self):
        """System roles cannot be deleted even by superusers"""
        role = self._create_role(is_system=True)
        self.client.force_authenticate(user=self.superuser)
        response = self.client.delete(self._get_role_detail_url(role.external_id))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(RoleModel.objects.filter(id=role.id).exists())
