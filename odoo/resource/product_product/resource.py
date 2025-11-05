from care.emr.models.charge_item_definition import ChargeItemDefinition
from care.emr.models.product import Product
from care.emr.resources.common.monetary_component import MonetaryComponentType
from odoo.connector.connector import OdooConnector
from odoo.resource.product_category.spec import CategoryData
from odoo.resource.product_product.spec import ProductData, TaxData


class OdooProductProductResource:
    def get_charge_item_base_price(self, charge_item: ChargeItemDefinition):
        for item in charge_item.price_components:
            if item["monetary_component_type"] == MonetaryComponentType.base.value:
                return item["amount"]
        raise Exception("Base price not found")

    def get_charge_item_purchase_price(self, charge_item: ChargeItemDefinition):
        for item in charge_item.price_components:
            if (
                item["monetary_component_type"]
                == MonetaryComponentType.informational.value
                and item["code"]["code"] == "purchase_price"
            ):
                return item["amount"]
        return None

    def get_charge_item_mrp(self, charge_item: ChargeItemDefinition):
        for item in charge_item.price_components:
            if (
                item["monetary_component_type"]
                == MonetaryComponentType.informational.value
                and item["code"]["code"] == "mrp"
            ):
                return item["amount"]
        return None

    def get_taxes(self, charge_item: ChargeItemDefinition):
        taxes = []
        for item in charge_item.price_components:
            if item["monetary_component_type"] == MonetaryComponentType.tax.value:
                taxes.append(item)
        return taxes

    def sync_product_to_odoo_api(
        self, charge_item_definition, hsn: str = ""
    ) -> int | None:
        """
        Synchronize a charge item definition to Odoo as a product.

        Args:
            charge_item_definition: ChargeItemDefinition instance

        Returns:
            Odoo product ID if successful, None otherwise
        """
        base_price = self.get_charge_item_base_price(charge_item_definition)
        mrp = self.get_charge_item_mrp(charge_item_definition)
        purchase_price = self.get_charge_item_purchase_price(charge_item_definition)

        taxes = []
        for tax in self.get_taxes(charge_item_definition):
            taxes.append(
                TaxData(
                    tax_name=tax["code"]["display"],
                    tax_percentage=float(tax["factor"]),
                )
            )
        data = ProductData(
            product_name=f"CARE: {charge_item_definition.title}",
            x_care_id=str(charge_item_definition.external_id),
            mrp=float(base_price or "0"),
            cost=float(purchase_price or mrp or "0"),
            category=CategoryData(
                category_name=charge_item_definition.category.title,
                parent_x_care_id=str(charge_item_definition.category.parent.external_id)
                if charge_item_definition.category.parent
                else "",
                x_care_id=str(charge_item_definition.category.external_id),
            ),
            taxes=taxes,
            hsn=hsn,
        ).model_dump()

        response = OdooConnector.call_api("api/add/product", data)
        return response.get("product", {}).get("id")

    def sync_product_from_product_model(self, product: Product) -> int | None:
        """
        Synchronize a product to Odoo if it has a charge item definition.

        Args:
            product: Product instance

        Returns:
            Odoo product ID if successful, None otherwise
        """
        if not product.charge_item_definition:
            return None

        hsn = (
            product.product_knowledge.alternate_identifier
            if product.product_knowledge
            and product.product_knowledge.alternate_identifier
            else ""
        )

        return self.sync_product_to_odoo_api(product.charge_item_definition, hsn)
