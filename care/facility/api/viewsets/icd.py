from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.icd import ICDSerializer
from care.facility.models.icd import ICDDisease
from care.facility.tasks.icd.scrape_icd import scrape_icd


class ICDFilterSet(filters.FilterSet):
    label = filters.CharFilter(field_name="label", lookup_expr="icontains")


class ICDViewSet(RetrieveModelMixin, ListModelMixin, CreateModelMixin, GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = ICDSerializer
    queryset = ICDDisease.objects.filter(is_leaf=True)
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = ICDFilterSet

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)
        if not is_many:
            return super(ICDViewSet, self).create(request, *args, **kwargs)

        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class ICDScrapeView(APIView):
    permission_classes = (IsAdminUser,)

    def get(self, request):
        scrape_icd.apply_async()
        return Response("Scraping Started", status=status.HTTP_200_OK)
