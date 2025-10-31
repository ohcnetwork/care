import logging

from care.emr.models.payment_reconciliation import PaymentReconciliation
from care.emr.resources.payment_reconciliation.spec import (
    PaymentReconciliationPaymentMethodOptions,
)
from odoo.connector.connector import OdooConnector
from odoo.resource.account_move_payment.spec import (
    AccountMovePaymentApiRequest,
    JournalType,
    PaymentMode,
)
from odoo.resource.base import OdooBaseResource
from odoo.resource.res_partner.spec import PartnerData, PartnerType

logger = logging.getLogger(__name__)


class OdooPaymentResource(OdooBaseResource):
    resource_name = "account.payment"

    def sync_payment_to_odoo_api(self, payment_id: str) -> int | None:
        """
        Synchronize a Django payment reconciliation to Odoo using the custom addon API.

        Args:
            payment_id: External ID of the Django payment reconciliation

        Returns:
            Odoo payment ID if successful, None otherwise
        """
        payment = PaymentReconciliation.objects.select_related(
            "facility", "account", "target_invoice"
        ).get(external_id=payment_id)

        # Prepare partner data
        partner_data = PartnerData(
            name=payment.account.patient.name,
            x_care_id=str(payment.account.patient.external_id),
            partner_type=PartnerType.person,
            phone=payment.account.patient.phone_number,
            state=payment.facility.state or "kerala",
            email="",
            agent=False,
        )

        # Prepare payment data
        data = AccountMovePaymentApiRequest(
            journal_x_care_id=str(
                payment.target_invoice.external_id if payment.target_invoice else ""
            ),
            x_care_id=str(payment.external_id),
            amount=float(payment.amount),
            journal_input=JournalType.cash
            if payment.method == PaymentReconciliationPaymentMethodOptions.cash.value
            else JournalType.bank,
            payment_date=payment.payment_datetime.strftime("%Y-%m-%d"),
            payment_mode=PaymentMode.send
            if payment.is_credit_note
            else PaymentMode.receive,
            partner_data=partner_data,
        ).model_dump()

        logger.info("Odoo Payment Data: %s", data)

        response = OdooConnector.call_api("api/account/move/payment", data)
        return response["payment"]["id"]
