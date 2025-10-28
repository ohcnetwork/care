from care.users.models import User
from odoo.connector.connector import OdooConnector
from odoo.resource.base import OdooBaseResource
from odoo.resource.res_partner.spec import PartnerData, PartnerType
from odoo.resource.res_user.spec import UserData, UserType


class OdooUserResource(OdooBaseResource):
    resource_name = "res.users"

    def get_full_name(self, user: User):
        name = [user.prefix, user.first_name, user.last_name, user.suffix]
        name = " ".join(filter(None, [x.strip() if x else None for x in name]))
        return name or user.username or "-"

    def sync_user_to_odoo_api(self, user) -> int | None:
        """
        Synchronize a user to Odoo.

        Args:
            user: User instance

        Returns:
            Odoo user ID if successful, None otherwise
        """
        # Create partner data first
        partner_data = PartnerData(
            name=self.get_full_name(user),
            x_care_id=str(user.external_id),
            partner_type=PartnerType.person,
            phone=user.phone_number,
            state="kerala",  # Default to Kerala
            email=user.email,
            agent=True,
        )

        # Create user data
        data = UserData(
            name=self.get_full_name(user),
            login=user.username,
            email=user.email,
            user_type=UserType.internal,  # Default to internal user
            phone=user.phone_number,
            state="kerala",  # Default to Kerala
            partner_data=partner_data,
        ).model_dump()

        response = OdooConnector.call_api("api/add/user", data)
        return response.get("user", {}).get("id")
