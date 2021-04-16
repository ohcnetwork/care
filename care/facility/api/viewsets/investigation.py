from care.facility.api.serializers.investigation import InvestigationSerializer
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from care.facility.models.investigation import Investigation
from django.db import transaction
from rest_framework.response import Response
from care.facility.models import User


class InvestigationViewset(viewsets.ModelViewSet):
    queryset = Investigation.objects.all()
    serializer_class = InvestigationSerializer
    lookup_field = "external_id"
    permission_classes = (IsAuthenticated, )

    def get_queryset(self):
        if self.request.user.is_superuser:
            return self.queryset
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            return self.queryset.filter(patient__facility__state=self.request.user.state)
        elif self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            return self.queryset.filter(patient__facility__district=self.request.user.district)
        filters = Q(patient__facility__users__id__exact=self.request.user.id)
        filters |= Q(assigned_to=self.request.user)
        return self.queryset.filter(filters).distinct("id")

    def create(self, request, *args, **kwargs):
        # print(request.user)
        with transaction.atomic():
            if(request.user.user_type < User.TYPE_VALUE_MAP["Staff"]):
                return Response({"status": "Access denied"}, status=status.HTTP_403_FORBIDDEN)

            return super(InvestigationViewset, self).create(request, *args, **kwargs)
