from django.forms.models import model_to_dict
from django.urls import reverse
from polyfactory.factories.pydantic_factory import ModelFactory
from rest_framework import status

from care.emr.resources.patient.spec import GenderChoices
from care.emr.resources.user.spec import (
    UserCreateSpec,
    UserTypeOptions,
    UserTypeRoleMapping,
)
from care.security.permissions.user import UserPermissions
from care.utils.tests.base import CareAPITestBase


class UserFactory(ModelFactory[UserCreateSpec]):
    __model__ = UserCreateSpec


class UserTestEdit(CareAPITestBase):
    """
    Test cases for checking edit user

    Tests should check if permission is checked when user is edited
    """

    def setUp(self):
        self.organization = self.create_organization(org_type="govt")
        self.organization2 = self.create_organization(org_type="govt")
        role = self.create_role_with_permissions(
            permissions=[UserPermissions.can_create_user.name]
        )
        self.user = self.create_user(
            first_name="Test",
            last_name="User",
            gender=GenderChoices.non_binary,
            geo_organization=self.organization,
            user_type=UserTypeOptions.doctor,
        )
        self.attach_role_organization_user(self.organization, self.user, role)
        self.create_role(
            name=UserTypeRoleMapping[self.user.user_type.value].value.name,
            is_system=True,
        )
        self.base_url = reverse("users-detail", kwargs={"username": self.user.username})

    def get_user_data(self, **kwargs):
        user_data = model_to_dict(self.user)
        user_data.update(kwargs)
        return user_data

    def test_edit_user_unauthenticated(self):
        response = self.client.put(
            self.base_url,
            self.get_user_data(first_name="Test Edit User"),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_user_authorization(self):
        self.client.force_authenticate(user=self.user)
        user_data = self.get_user_data(
            first_name="Test Edit User",
            gender=GenderChoices.female,
            geo_organization=self.organization.external_id,
        )
        response = self.client.put(self.base_url, user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["first_name"], "Test Edit User")
        self.assertEqual(response.data["gender"], "female")

    def test_edit_user_change_geo_organization(self):
        self.client.force_authenticate(user=self.user)
        user_data = self.get_user_data(geo_organization=self.organization2.external_id)
        response = self.client.put(self.base_url, user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["geo_organization"]["id"], str(self.organization2.external_id)
        )
