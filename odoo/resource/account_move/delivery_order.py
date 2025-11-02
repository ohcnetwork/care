import logging

from care.emr.models.supply_delivery import DeliveryOrder, SupplyDelivery
from care.emr.resources.common.monetary_component import MonetaryComponentType
from care.emr.resources.inventory.supply_delivery.spec import (
    SupplyDeliveryStatusOptions,
)
from odoo.connector.connector import OdooConnector
from odoo.resource.account_move.spec import (
    AccountMoveApiRequest,
    BillType,
    InvoiceItem,
)
from odoo.resource.product_category.spec import CategoryData
from odoo.resource.product_product.spec import ProductData
from odoo.resource.res_partner.spec import PartnerData, PartnerType

logger = logging.getLogger(__name__)


class OdooDeliveryOrderResource:
    def get_product_base_price(self, product):
        """Get base price from charge item definition price components"""
        if not product.charge_item_definition:
            return "0"

        for item in product.charge_item_definition.price_components:
            if item["monetary_component_type"] == MonetaryComponentType.base.value:
                return item["amount"]
        return "0"

    def get_product_purchase_price(self, product):
        """Get purchase price from charge item definition price components"""
        if not product.charge_item_definition:
            return None

        for item in product.charge_item_definition.price_components:
            if (
                item["monetary_component_type"]
                == MonetaryComponentType.informational.value
                and item["code"]["code"] == "purchase_price"
            ):
                return item["amount"]
        return None

    def sync_delivery_order_to_odoo_api(self, delivery_order_id: str) -> int | None:
        """
        Synchronize a Django delivery order to Odoo as a vendor bill using the custom addon API.

        Args:
            delivery_order_id: External ID of the Django delivery order

        Returns:
            Odoo invoice ID if successful, None otherwise
        """
        delivery_order = DeliveryOrder.objects.select_related(
            "supplier", "destination", "destination__facility"
        ).get(external_id=delivery_order_id)

        # Prepare partner data for supplier
        supplier_metadata = delivery_order.supplier.metadata or {}
        partner_data = PartnerData(
            name=delivery_order.supplier.name,
            x_care_id=str(delivery_order.supplier.external_id),
            partner_type=PartnerType.company,
            phone=supplier_metadata.get("phone", ""),
            state=supplier_metadata.get("state", "kerala"),
            email=supplier_metadata.get("email", ""),
            agent=False,
        )

        # Prepare invoice items from supply deliveries
        invoice_items = []
        supply_deliveries = SupplyDelivery.objects.filter(
            order=delivery_order, status=SupplyDeliveryStatusOptions.completed.value
        ).select_related(
            "supplied_item",
            "supplied_item__charge_item_definition",
            "supplied_item__charge_item_definition__category",
            "supplied_item__charge_item_definition__category__parent",
            "supplied_item__product_knowledge",
        )

        for supply_delivery in supply_deliveries:
            if supply_delivery.supplied_item:
                product = supply_delivery.supplied_item
                base_price = self.get_product_base_price(product)
                purchase_price = self.get_product_purchase_price(product)

                # Get category data if charge item definition exists
                if (
                    product.charge_item_definition
                    and product.charge_item_definition.category
                ):
                    category_data = CategoryData(
                        category_name=product.charge_item_definition.category.title,
                        parent_x_care_id=str(
                            product.charge_item_definition.category.parent.external_id
                        )
                        if product.charge_item_definition.category.parent
                        else "",
                        x_care_id=str(
                            product.charge_item_definition.category.external_id
                        ),
                    )
                else:
                    category_data = CategoryData(
                        category_name="Uncategorized",
                        parent_x_care_id="",
                        x_care_id="",
                    )

                product_data = ProductData(
                    product_name=product.product_knowledge.name
                    if product.product_knowledge
                    else "Unknown Product",
                    x_care_id=str(product.external_id),
                    mrp=float(base_price or "0"),
                    cost=float(purchase_price or base_price or "0"),
                    category=category_data,
                )

                item = InvoiceItem(
                    product_data=product_data,
                    quantity=str(supply_delivery.supplied_item_quantity or 0),
                    sale_price=str(purchase_price or base_price or "0"),
                    x_care_id=str(supply_delivery.external_id),
                )

                invoice_items.append(item)

        logger.info("Delivery Order Items: %s", invoice_items)

        # Prepare final data using our spec with vendor bill type
        data = AccountMoveApiRequest(
            partner_data=partner_data,
            invoice_items=invoice_items,
            invoice_date=delivery_order.created_date.strftime("%d-%m-%Y"),
            x_care_id=str(delivery_order.external_id),
            bill_type=BillType.vendor,
            due_date=delivery_order.created_date.strftime("%d-%m-%Y"),
            reason="",
        ).model_dump()

        logger.info("Odoo Delivery Order Data: %s", data)

        response = OdooConnector.call_api("api/account/move", data)
        return response["invoice"]["id"]
