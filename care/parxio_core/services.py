import hashlib
import hmac
from datetime import date
from decimal import Decimal

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from slugify import slugify

from care.emr.models.encounter import Encounter
from care.emr.models.medication_request import MedicationRequestPrescription
from care.facility.models import Facility
from care.parxio_core.models import BridgeSyncStatus, MonthlyIncentive, Tenant, TenantPlanTier

User = get_user_model()


class ProvisioningService:
    @staticmethod
    def _extract_order_notes(payload: dict) -> dict:
        return (
            payload.get("payload", {})
            .get("payment", {})
            .get("entity", {})
            .get("notes", {})
            or {}
        )

    @classmethod
    def _build_unique_subdomain(cls, preferred: str, tenant_name: str) -> str:
        base = slugify(preferred or tenant_name or "clinic").replace("-", "")
        base = (base or "clinic")[:24]
        candidate = base
        suffix = 1
        while Tenant.objects.filter(subdomain=candidate).exists():
            suffix += 1
            candidate = f"{base[:20]}{suffix}"
        return candidate

    @classmethod
    def provision_from_payment(cls, payload: dict) -> dict:
        notes = cls._extract_order_notes(payload)
        payment = payload.get("payload", {}).get("payment", {}).get("entity", {}) or {}

        clinic_name = notes.get("clinic_name") or notes.get("tenant_name") or "Parxio Clinic"
        subdomain = cls._build_unique_subdomain(
            notes.get("subdomain") or notes.get("doctor_name") or clinic_name,
            clinic_name,
        )
        email = notes.get("email") or f"{subdomain}@parxio.local"
        phone_number = notes.get("phone_number") or "+919696969696"
        doctor_name = notes.get("doctor_name") or clinic_name
        plan_tier = notes.get("plan_tier") or TenantPlanTier.LITE

        tenant, created = Tenant.objects.get_or_create(
            subdomain=subdomain,
            defaults={
                "name": clinic_name,
                "plan_tier": plan_tier,
                "abdm_bridge_id": notes.get("abdm_bridge_id", ""),
                "metadata": {
                    "source": "razorpay_webhook",
                    "payment_id": payment.get("id"),
                    "order_id": payment.get("order_id"),
                },
            },
        )

        username = cls._build_unique_subdomain(notes.get("username") or doctor_name, doctor_name)
        admin_password = User.objects.make_random_password()
        admin_user, user_created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "first_name": doctor_name.split()[0],
                "last_name": " ".join(doctor_name.split()[1:])[:150],
                "phone_number": phone_number,
                "user_type": "administrator",
                "gender": "non_binary",
                "verified": True,
            },
        )
        if user_created:
            admin_user.set_password(admin_password)
            admin_user.save(update_fields=["password"])

        facility = Facility.objects.filter(tenant=tenant).first()
        if facility is None:
            facility = Facility.objects.create(
                tenant=tenant,
                name=f"{clinic_name} Clinic",
                description="Auto-provisioned default clinic for Parxio onboarding",
                address=notes.get("address") or "Address pending during onboarding",
                phone_number=phone_number,
                facility_type=2,
                created_by=admin_user,
            )

        if admin_user.home_facility_id != facility.id:
            admin_user.home_facility = facility
            admin_user.save(update_fields=["home_facility"])

        return {
            "tenant": tenant,
            "facility": facility,
            "admin_user": admin_user,
            "admin_password": admin_password if user_created else None,
            "success_url": f"https://{tenant.subdomain}.parxio.in/setup-complete",
            "created": created,
        }


class ABDMService:
    parxio_cut = Decimal("5.00")
    doctor_cut = Decimal("20.00")

    @staticmethod
    def is_m2_compliant(encounter: Encounter, prescription: MedicationRequestPrescription | None = None) -> bool:
        if prescription is not None:
            return bool(prescription.pk)
        return MedicationRequestPrescription.objects.filter(encounter=encounter).exists()

    @staticmethod
    def _current_month(encounter: Encounter) -> date:
        source_date = encounter.modified_date or timezone.now()
        return date(source_date.year, source_date.month, 1)

    @classmethod
    def _bridge_endpoint(cls) -> str | None:
        return getattr(settings, "PARXIO_ABDM_BRIDGE_URL", None)

    @classmethod
    def _post_bridge(cls, payload: dict, tenant: Tenant) -> tuple[str, dict]:
        endpoint = cls._bridge_endpoint()
        if not endpoint or not tenant.abdm_bridge_id:
            return BridgeSyncStatus.SKIPPED, {}

        response = requests.post(
            endpoint,
            json=payload,
            headers={"X-Parxio-Bridge": tenant.abdm_bridge_id},
            timeout=15,
        )
        response.raise_for_status()
        return BridgeSyncStatus.SUCCESS, response.json() if response.content else {}

    @classmethod
    def sync_incentive(
        cls,
        encounter: Encounter,
        prescription: MedicationRequestPrescription | None = None,
    ) -> MonthlyIncentive | None:
        if not encounter.tenant_id or not cls.is_m2_compliant(encounter, prescription):
            return None

        doctor = (
            getattr(prescription, "prescribed_by", None)
            or getattr(encounter, "updated_by", None)
            or getattr(encounter, "created_by", None)
        )
        payload = {
            "tenant": encounter.tenant.subdomain,
            "encounter_id": str(encounter.external_id),
            "patient_id": str(encounter.patient.external_id),
            "facility_id": str(encounter.facility.external_id),
            "prescription_id": str(prescription.external_id) if prescription else None,
            "doctor_id": str(doctor.external_id) if doctor else None,
            "timestamp": timezone.now().isoformat(),
        }

        bridge_status = BridgeSyncStatus.PENDING
        bridge_response: dict = {}
        bridge_reference = ""
        try:
            bridge_status, bridge_response = cls._post_bridge(payload, encounter.tenant)
            bridge_reference = str(
                bridge_response.get("id")
                or bridge_response.get("reference_id")
                or ""
            )
        except Exception as exc:  # noqa: BLE001
            bridge_status = BridgeSyncStatus.FAILED
            bridge_response = {"error": str(exc)}

        incentive, _ = MonthlyIncentive.objects.update_or_create(
            tenant=encounter.tenant,
            encounter=encounter,
            month=cls._current_month(encounter),
            defaults={
                "patient": encounter.patient,
                "facility": encounter.facility,
                "doctor": doctor,
                "prescription": prescription,
                "is_m2_compliant": True,
                "parxio_cut": cls.parxio_cut,
                "doctor_cut": cls.doctor_cut,
                "bridge_status": bridge_status,
                "bridge_reference": bridge_reference,
                "bridge_response": bridge_response,
            },
        )
        return incentive


def verify_razorpay_signature(payload: bytes, signature: str | None) -> bool:
    secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
    if not secret or not signature:
        return True
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)
