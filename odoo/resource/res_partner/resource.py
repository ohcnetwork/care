from care.emr.models.organization import Organization
from odoo.connector.connector import OdooConnector
from odoo.resource.res_partner.spec import PartnerData, PartnerType


class OdooPartnerResource:
    def sync_partner_to_odoo_api(self, organization: Organization) -> int | None:
        """
        Synchronize an organization to Odoo as a partner.

        Args:
            organization: Organization instance

        Returns:
            Odoo partner ID if successful, None otherwise
        """
        # Extract contact information from metadata
        metadata = organization.metadata or {}
        email = metadata.get("email", "")
        phone = metadata.get("phone", "")
        state = metadata.get("state", "kerala")

        data = PartnerData(
            name=organization.name,
            x_care_id=str(organization.external_id),
            email=email,
            phone=phone,
            state=state,
            partner_type=PartnerType.company,
            agent=False,
        ).model_dump()

        response = OdooConnector.call_api("api/add/partner", data)
        return response.get("partner", {}).get("id")
