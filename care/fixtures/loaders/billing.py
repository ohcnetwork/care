from datetime import timedelta

from care.fixtures.loaders.load import load_json
from care.utils.time_util import care_now

_ACCOUNT_META = frozenset({"ref", "patient_ref", "encounter_ref"})
_PAYMENT_META = frozenset({"ref", "invoice_ref", "days_ago"})


def load_billing(
    base,
    facility_id,
    patient_ids_by_ref,
    encounter_ids_by_ref,
    charge_item_definitions_by_ref,
):
    pack = load_json("billing")
    now = care_now()
    performer = str(base.user.external_id)
    patient_name_by_ref = {
        row["ref"]: row["name"] for row in load_json("patients").get("patients", [])
    }

    base.set_invoice_expression(facility_id, pack["invoice_number_expression"])

    accounts_by_ref, patient_id_by_account_ref = _load_accounts(
        base,
        facility_id,
        pack.get("accounts", []),
        patient_ids_by_ref,
        encounter_ids_by_ref,
        patient_name_by_ref,
        now,
    )
    invoices_by_ref, account_id_by_invoice_ref = _load_invoices(
        base,
        facility_id,
        pack.get("invoices", []),
        accounts_by_ref,
        patient_id_by_account_ref,
        charge_item_definitions_by_ref,
        performer,
        now,
    )
    _load_payments(
        base,
        facility_id,
        pack.get("payments", []),
        invoices_by_ref,
        account_id_by_invoice_ref,
        now,
    )


def _load_accounts(
    base,
    facility_id,
    rows,
    patient_ids_by_ref,
    encounter_ids_by_ref,
    patient_name_by_ref,
    now,
):
    accounts_by_ref: dict[str, object] = {}
    patient_id_by_account_ref: dict[str, str] = {}

    for entry in rows:
        ref = entry["ref"]
        patient_ref = entry["patient_ref"]
        patient_id = patient_ids_by_ref[patient_ref]
        payload = {k: v for k, v in entry.items() if k not in _ACCOUNT_META}
        payload.setdefault("name", f"{patient_name_by_ref[patient_ref]} {now:%Y-%m-%d}")
        account, created = _get_or_create_account(
            base, facility_id, patient_id, **payload
        )
        updates = {}
        if not created:
            updates.update(payload)
        encounter_ref = entry.get("encounter_ref")
        if encounter_ref and not getattr(account, "primary_encounter", None):
            updates["primary_encounter"] = encounter_ids_by_ref[encounter_ref]
        if updates:
            account = base.update_account(facility_id, account, **updates)
        accounts_by_ref[ref] = account
        patient_id_by_account_ref[ref] = patient_id

    return accounts_by_ref, patient_id_by_account_ref


def _load_invoices(
    base,
    facility_id,
    rows,
    accounts_by_ref,
    patient_id_by_account_ref,
    charge_item_definitions_by_ref,
    performer,
    now,
):
    invoices_by_ref: dict[str, object] = {}
    account_id_by_invoice_ref: dict[str, str] = {}

    for entry in rows:
        account_ref = entry["account_ref"]
        account = accounts_by_ref[account_ref]
        patient_id = patient_id_by_account_ref[account_ref]
        status = entry["status"]
        days_ago = entry["days_ago"]

        before = {ci.id for ci in base.list_charge_items(facility_id, account.id)}
        requests = [
            {
                "quantity": str(item["quantity"]),
                "charge_item_definition": charge_item_definitions_by_ref[
                    item["charge_item_definition_ref"]
                ]["slug"],
                "patient": patient_id,
                "account": account.id,
                "performer_actor": performer,
            }
            for item in entry["charge_items"]
        ]
        base.apply_charge_item_defs(facility_id, requests)
        charge_item_ids = [
            charge_item.id
            for charge_item in base.list_charge_items(facility_id, account.id)
            if charge_item.id not in before
        ]

        created = now - timedelta(days=days_ago)
        invoice = base.create_invoice(
            facility_id,
            account.id,
            charge_item_ids,
            created_date=created,
        )

        if status == "entered_in_error":
            invoice = base.cancel_invoice(
                facility_id, invoice, reason="entered_in_error"
            )
        elif status != "draft":
            invoice = base.issue_invoice(
                facility_id, invoice, issue_date=created.isoformat()
            )
            if status == "cancelled":
                invoice = base.cancel_invoice(facility_id, invoice, reason="cancelled")

        invoices_by_ref[entry["ref"]] = invoice
        account_id_by_invoice_ref[entry["ref"]] = account.id

    return invoices_by_ref, account_id_by_invoice_ref


def _load_payments(
    base,
    facility_id,
    rows,
    invoices_by_ref,
    account_id_by_invoice_ref,
    now,
):
    for entry in rows:
        invoice_ref = entry["invoice_ref"]
        invoice = invoices_by_ref[invoice_ref]
        account_id = account_id_by_invoice_ref[invoice_ref]
        payload = {k: v for k, v in entry.items() if k not in _PAYMENT_META}
        tendered_amount = payload.pop("tendered_amount", str(invoice.total_gross))
        returned_amount = payload.pop("returned_amount", 0)
        payload.setdefault(
            "payment_datetime",
            (now - timedelta(days=entry["days_ago"])).isoformat(),
        )
        base.create_payment_reconciliation(
            facility_id,
            account_id,
            tendered_amount,
            returned_amount=returned_amount,
            target_invoice=invoice.id,
            **payload,
        )
        base.balance_invoice(facility_id, invoice)


def _get_or_create_account(base, facility_id, patient_id, **payload):
    existing = base.list_accounts(
        facility_id,
        patient=patient_id,
        status="active",
        billing_status="open",
    )
    if existing:
        return existing[0], False
    return base.create_account(facility_id, patient_id, **payload), True
