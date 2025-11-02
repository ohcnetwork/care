from odoo.connector.connector import OdooConnector
from odoo.resource.product_category.spec import CategoryData


class OdooCategoryResource:
    def sync_category_to_odoo_api(self, category) -> int | None:
        """
        Synchronize a resource category to Odoo.

        Args:
            category: ResourceCategory instance

        Returns:
            Odoo category ID if successful, None otherwise
        """
        data = CategoryData(
            category_name=category.title,
            parent_x_care_id=str(category.parent.external_id)
            if category.parent
            else "",
            x_care_id=str(category.external_id),
        ).model_dump()

        response = OdooConnector.call_api("api/add/category", data)
        return response.get("category", {}).get("id")
