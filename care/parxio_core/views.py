import json

from django.db.models import Sum
from django.http import JsonResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.views import APIView

from care.parxio_core.models import MonthlyIncentive
from care.parxio_core.services import ProvisioningService, verify_razorpay_signature


class CurrentTenantView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        tenant = getattr(request, "current_tenant", None)
        if not tenant:
            return JsonResponse(
                {
                    "tenant": None,
                    "subdomain": None,
                    "brand_name": "Parxio",
                    "logo_url": None,
                    "plan_tier": None,
                    "is_admin_host": True,
                }
            )
        return JsonResponse(
            {
                "tenant": str(tenant.external_id),
                "subdomain": tenant.subdomain,
                "brand_name": tenant.name,
                "logo_url": tenant.logo_url or None,
                "plan_tier": tenant.plan_tier,
                "is_admin_host": False,
            }
        )


class RazorpayWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        payload = request.body
        signature = request.headers.get("X-Razorpay-Signature")
        if not verify_razorpay_signature(payload, signature):
            return JsonResponse({"detail": "Invalid signature"}, status=400)

        body = json.loads(payload.decode("utf-8") or "{}")
        if body.get("event") != "payment.authorized":
            return JsonResponse({"detail": "Ignored"}, status=202)

        result = ProvisioningService.provision_from_payment(body)
        return JsonResponse(
            {
                "detail": "Provisioning triggered",
                "success_url": result["success_url"],
                "tenant": str(result["tenant"].external_id),
                "facility": str(result["facility"].external_id),
                "admin_user": result["admin_user"].username,
            }
        )


class MonthlyIncentiveSummaryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, facility_external_id):
        queryset = MonthlyIncentive.objects.filter(facility__external_id=facility_external_id)
        if request.user.user_type == "doctor":
            queryset = queryset.filter(doctor=request.user)

        month = request.query_params.get("month")
        if month:
            queryset = queryset.filter(month=month)

        summary = queryset.aggregate(
            doctor_total=Sum("doctor_cut"),
            parxio_total=Sum("parxio_cut"),
        )
        patient_count = queryset.values("patient_id").distinct().count()

        return JsonResponse(
            {
                "doctor_total": str(summary["doctor_total"] or 0),
                "parxio_total": str(summary["parxio_total"] or 0),
                "patient_count": patient_count,
                "threshold_target": 100,
                "threshold_progress": min(patient_count, 100),
            }
        )
