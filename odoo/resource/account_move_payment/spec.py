from enum import Enum

from pydantic import BaseModel

from odoo.resource.res_partner.spec import PartnerData


class JournalType(str, Enum):
    cash = "cash"
    bank = "bank"


class PaymentMode(str, Enum):
    send = "send"
    receive = "receive"


class AccountMovePaymentApiRequest(BaseModel):
    x_care_id: str
    journal_x_care_id: str | None = None
    amount: float = 0.0
    journal_input: JournalType
    payment_date: str
    payment_mode: PaymentMode
    partner_data: PartnerData
