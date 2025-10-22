from typing import Any

from odoo.resource.base import OdooBaseResource


class OdooAgentResource(OdooBaseResource):
    resource_name = "res.partner"

    def create_agent(
        self,
        name: str,
        care_id: str,
        email: str | None = None,
        phone: str | None = None,
        mobile: str | None = None,
        street: str | None = None,
        street2: str | None = None,
        city: str | None = None,
        state_id: int | None = None,
        country_id: int | None = None,
        zip_code: str | None = None,
        vat: str | None = None,
        ref: str | None = None,
        comment: str | None = None,
        is_company: bool = True,  # Changed default to True
    ) -> int:
        """
        Create a new agent (doctor) in Odoo.

        Args:
            name: Agent name
            care_id: Care external ID
            email: Email address
            phone: Phone number
            mobile: Mobile number
            street: Street address
            street2: Additional street address
            city: City
            state_id: State/Province ID
            country_id: Country ID
            zip_code: ZIP/Postal code
            vat: VAT number
            ref: Reference number
            comment: Additional notes
            is_company: Whether this is a company (defaults to True for agents)

        Returns:
            ID of the created agent
        """
        agent_data = {
            "name": name,
            "is_company": is_company,
            "supplier_rank": 1,  # Mark as supplier/agent
            "customer_rank": 0,
            "x_care_id": care_id,
            "agent": True,  # Added this field
        }

        # Add optional fields
        agent_data["email"] = email if email else ""
        agent_data["phone"] = phone if phone else ""
        agent_data["mobile"] = mobile if mobile else ""
        agent_data["street"] = street if street else ""
        agent_data["street2"] = street2 if street2 else ""
        agent_data["zip"] = zip_code if zip_code else ""
        agent_data["category_id"] = None
        agent_data["city"] = city if city else ""
        agent_data["state_id"] = state_id if state_id else ""
        agent_data["country_id"] = country_id if country_id else ""
        agent_data["vat"] = vat if vat else ""
        agent_data["ref"] = ref if ref else ""

        return self.get_odoo_model().create(agent_data)

    def find_by_care_id(self, care_id: str) -> dict[str, Any] | None:
        """
        Find an agent by Care ID.
        """
        model = self.get_odoo_model()
        results = model.search([("x_care_id", "=", care_id)], limit=1)
        if results and len(results) != 0:
            return results[0]
        return None

    def get_or_create_doctor_agent(self, user) -> int:
        """
        Get or create an agent for a doctor user.
        """
        from odoo.models import UserOdooAgent

        # First check if we already have a mapping
        try:
            user_agent = UserOdooAgent.objects.get(user=user)
            return user_agent.odoo_agent_id
        except UserOdooAgent.DoesNotExist:
            # No mapping exists, create new agent in Odoo
            user_name = f"CARE : {user.get_full_name()}"
            user_id = str(user.external_id)
            existing_agent_id = self.find_by_care_id(user_id)
            if not existing_agent_id:
                existing_agent_id = self.create_agent(
                    name=user_name,
                    phone=user.phone_number,
                    email=user.email,
                    care_id=user_id,
                )

            # Create the mapping
            UserOdooAgent.objects.create(user=user, odoo_agent_id=existing_agent_id)
            return existing_agent_id
