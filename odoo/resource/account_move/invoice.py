import logging

from care.emr.models.charge_item import ChargeItem
from care.emr.models.invoice import Invoice
from care.emr.models.medication_dispense import MedicationDispense
from care.emr.models.scheduling.booking import TokenBooking
from care.emr.models.service_request import ServiceRequest
from care.emr.resources.charge_item.spec import ChargeItemResourceOptions
from care.emr.resources.common.monetary_component import MonetaryComponentType
from odoo.connector.connector import OdooConnector
from odoo.resource.account_move.spec import (
    AccountMoveApiRequest,
    AccountMoveReturnApiRequest,
    BillType,
    InvoiceItem,
)
from odoo.resource.product_category.spec import CategoryData
from odoo.resource.product_product.spec import ProductData
from odoo.resource.res_partner.spec import PartnerData, PartnerType

logger = logging.getLogger(__name__)


class OdooInvoiceResource:
    def get_charge_item_base_price(self, charge_item: ChargeItem):
        for item in charge_item.unit_price_components:
            if item["monetary_component_type"] == MonetaryComponentType.base.value:
                return item["amount"]
        raise Exception("Base price not found")

    def get_charge_item_purchase_price(self, charge_item: ChargeItem):
        for item in charge_item.unit_price_components:
            if (
                item["monetary_component_type"]
                == MonetaryComponentType.informational.value
                and item["code"]["code"] == "purchase_price"
            ):
                return item["amount"]
        return None

    def get_charge_item_mrp(self, charge_item: ChargeItem):
        for item in charge_item.unit_price_components:
            if (
                item["monetary_component_type"]
                == MonetaryComponentType.informational.value
                and item["code"]["code"] == "mrp"
            ):
                return item["amount"]
        return None

    def sync_invoice_to_odoo_api(self, invoice_id: str) -> int | None:
        """
        Synchronize a Django invoice to Odoo using the custom addon API.

        Args:
            invoice_id: External ID of the Django invoice

        Returns:
            Odoo invoice ID if successful, None otherwise
        """
        invoice = Invoice.objects.select_related("facility", "patient").get(
            external_id=invoice_id
        )

        # Prepare partner data
        partner_data = PartnerData(
            name=invoice.patient.name,
            x_care_id=str(invoice.patient.external_id),
            partner_type=PartnerType.person,
            phone=invoice.patient.phone_number,
            state=invoice.facility.state or "kerala",
            email="",
            agent=False,
        )

        # Prepare invoice items
        invoice_items = []
        for charge_item in ChargeItem.objects.filter(
            paid_invoice=invoice
        ).select_related("charge_item_definition"):
            if charge_item.charge_item_definition:
                base_price = self.get_charge_item_base_price(charge_item)
                purchase_price = self.get_charge_item_purchase_price(charge_item)
                product_data = ProductData(
                    product_name=charge_item.charge_item_definition.title,
                    x_care_id=str(charge_item.charge_item_definition.external_id),
                    mrp=float(base_price or "0"),
                    cost=float(purchase_price or base_price or "0"),
                    category=CategoryData(
                        category_name=charge_item.charge_item_definition.category.title,
                        parent_x_care_id=str(
                            charge_item.charge_item_definition.category.parent.external_id
                        )
                        if charge_item.charge_item_definition.category.parent
                        else "",
                        x_care_id=str(
                            charge_item.charge_item_definition.category.external_id
                        ),
                    ),
                    status=charge_item.charge_item_definition.status,
                )

                item = InvoiceItem(
                    product_data=product_data,
                    quantity=str(charge_item.quantity),
                    sale_price=str(base_price),
                    x_care_id=str(charge_item.external_id),
                )

                if (
                    charge_item.service_resource
                    == ChargeItemResourceOptions.service_request.value
                ):
                    service_request = ServiceRequest.objects.get(
                        external_id=charge_item.service_resource_id
                    )
                    requester = service_request.requester
                elif (
                    charge_item.service_resource
                    == ChargeItemResourceOptions.appointment.value
                ):
                    token_booking = TokenBooking.objects.get(
                        external_id=charge_item.service_resource_id
                    )
                    requester = token_booking.token_slot.resource.user
                elif (
                    charge_item.service_resource
                    == ChargeItemResourceOptions.medication_dispense.value
                ):
                    medication_dispense = MedicationDispense.objects.get(
                        external_id=charge_item.service_resource_id
                    )
                    requester = (
                        medication_dispense.authorizing_request.requester
                        if medication_dispense.authorizing_request
                        else None
                    )
                else:
                    requester = None

                if requester:
                    item.agent_id = str(requester.external_id)
                invoice_items.append(item)

        logger.info("Invoice Items: %s", invoice_items)
        data = AccountMoveApiRequest(
            partner_data=partner_data,
            invoice_items=invoice_items,
            invoice_date=invoice.created_date.strftime("%d-%m-%Y"),
            x_care_id=str(invoice.external_id),
            bill_type=BillType.customer,
            due_date=invoice.created_date.strftime("%d-%m-%Y"),
            reason="",
        ).model_dump()
        logger.info("Odoo Invoice Data: %s", data)

        response = OdooConnector.call_api("api/account/move", data)
        return response["invoice"]["id"]

    def sync_invoice_return_to_odoo_api(self, invoice_id: str) -> int | None:
        """
        Synchronize a cancelled Django invoice to Odoo using the custom addon API.

        Args:
            invoice_id: External ID of the Django invoice

        Returns:
            Odoo invoice ID if successful, None otherwise
        """
        invoice = Invoice.objects.select_related("facility", "patient").get(
            external_id=invoice_id
        )

        data = AccountMoveReturnApiRequest(
            x_care_id=str(invoice.external_id),
            reason=invoice.status,
        ).model_dump()

        logger.info("Odoo Invoice Return Data: %s", data)
        response = OdooConnector.call_api("api/account/move/return", data)
        return response["reverse_invoice"]["id"]
