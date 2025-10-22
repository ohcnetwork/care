import logging

from odoo.connector.connector import OdooConnector
from odoo.resource.base import OdooBaseResource

logger = logging.getLogger(__name__)


class OdooFieldManagerResource(OdooBaseResource):
    """Resource for managing Odoo model fields."""

    resource_name = "ir.model.fields"

    def _get_model_id(self, model_name: str) -> int:
        """Get the ID of a model by its name."""
        model = OdooConnector.get_model("ir.model")
        results = model.search([("model", "=", model_name)], limit=1)
        if not results:
            msg = f"Model {model_name} not found in Odoo"
            raise ValueError(msg)
        return results[0]

    def check_field_exists(self, model_name: str, field_name: str) -> bool:
        """Check if a field exists in a model."""
        model_id = self._get_model_id(model_name)
        results = self.get_odoo_model().search(
            [("model_id", "=", model_id), ("name", "=", field_name)], limit=1
        )
        return bool(results)

    def create_care_id_field(self, model_name: str) -> bool:
        """
        Create x_care_id field in the specified model if it doesn't exist.

        Args:
            model_name: The technical name of the Odoo model (e.g., 'res.partner', 'account.move')

        Returns:
            bool: True if field was created or already exists, False if creation failed
        """
        try:
            # Check if field already exists
            if self.check_field_exists(model_name, "x_care_id"):
                msg = f"x_care_id field already exists in {model_name}"
                logger.info(msg)
                return True

            # Get model ID
            model_id = self._get_model_id(model_name)

            # Field definition
            field_data = {
                "model_id": model_id,
                "name": "x_care_id",
                "field_description": "Care ID",
                "ttype": "char",  # Field type: char
                "state": "manual",  # Custom field
                "required": False,
                "store": True,
                "index": True,  # Index for better search performance
                "copied": True,  # Copy value on record duplication
            }

            # Create the field
            self.get_odoo_model().create(field_data)
            msg = f"Successfully created x_care_id field in {model_name}"
            logger.info(msg)
            return True

        except Exception as e:
            msg = f"Failed to create x_care_id field in {model_name}: {e!s}"
            logger.error(msg)
            return False

    def create_care_id_fields(self, model_names: list[str]) -> dict:
        """
        Create x_care_id field in multiple models.

        Args:
            model_names: List of model technical names

        Returns:
            dict: Dictionary with model names as keys and creation status as values
        """
        results = {}
        for model_name in model_names:
            results[model_name] = self.create_care_id_field(model_name)
        return results
