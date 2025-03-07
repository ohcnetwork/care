from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import BaseModel, Field
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.fhir.resources.code_concept import CodeConceptResource, MinimalCodeConcept
from care.emr.models.valueset import UserValueSetPreference, ValueSet
from care.emr.resources.common.coding import Coding
from care.emr.resources.valueset.spec import ValueSetReadSpec, ValueSetSpec


class ExpandRequest(BaseModel):
    search: str = ""
    count: int = Field(10, gt=0, lt=100)
    display_language: str = "en-gb"


class ValueSetFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")


class ValueSetViewSet(EMRModelViewSet):
    database_model = ValueSet
    pydantic_model = ValueSetSpec
    pydantic_read_model = ValueSetReadSpec
    filterset_class = ValueSetFilter
    filter_backends = [DjangoFilterBackend]
    lookup_field = "slug"

    def permissions_controller(self, request):
        if self.action in [
            "list",
            "retrieve",
            "lookup_code",
            "expand",
            "validate_code",
            "preview_search",
            "mark_favorite",
            "remove_favorite",
            "favorites",
            "recent_views",
        ]:
            return True
        # Only superusers have write permission over valuesets
        return request.user.is_superuser

    def get_queryset(self):
        return ValueSet.objects.all().select_related("created_by", "updated_by")

    def get_serializer_class(self):
        return ValueSetSpec

    @extend_schema(request=ExpandRequest, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def expand(self, request, *args, **kwargs):
        request_params = ExpandRequest(**request.data).model_dump()
        results = self.get_object().search(**request_params)
        return Response({"results": [result.model_dump() for result in results]})

    @extend_schema(request=ValueSetSpec, responses={200: None}, methods=["POST"])
    @action(detail=False, methods=["POST"])
    def preview_search(self, request, *args, **kwargs):
        # Get search parameters from query params
        search_text = request.query_params.get("search", "")
        count = int(request.query_params.get("count", 10))

        # Create temporary ValueSet object from request body
        valueset_data = ValueSetSpec(**request.data)
        temp_valueset = ValueSet(**valueset_data.model_dump())

        # Use the search parameters from query params
        results = temp_valueset.search(search=search_text, count=count)
        return Response({"results": [result.model_dump() for result in results]})

    @extend_schema(request=Coding, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def validate_code(self, request, *args, **kwargs):
        request_params = Coding(**request.data)
        result = self.get_object().lookup(request_params)
        return Response({"result": result})

    @extend_schema(request=Coding, responses={200: None}, methods=["POST"])
    @action(detail=False, methods=["POST"])
    def lookup_code(self, request, *args, **kwargs):
        Coding(**request.data)  # Validate
        result = (
            CodeConceptResource()
            .filter(
                code=request.data["code"], system=request.data["system"], property="*"
            )
            .get()
        )
        return Response(result)

    def _get_or_create_user_preferences(self, user, valueset) -> UserValueSetPreference:
        return UserValueSetPreference.objects.get_or_create(
            user=user,
            valueset=valueset,
            defaults={"favorite_codes": [], "recent_codes": []},
        )[0]

    @extend_schema(request=MinimalCodeConcept, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def mark_favorite(self, request, *args, **kwargs):
        valueset = self.get_object()
        code_obj = MinimalCodeConcept(**request.data)

        preferences = self._get_or_create_user_preferences(request.user, valueset)

        if len(preferences.get_favorites()) >= preferences.MAX_FAVORITES:
            raise ValidationError("Maximum number of favorites reached (50)")

        preferences.add_favorite(code_obj.model_dump())
        return Response({"message": f"Code {code_obj.code} marked as favorite"})

    @action(detail=True, methods=["POST"])
    def remove_favorite(self, request, *args, **kwargs):
        valueset = self.get_object()
        code_obj = MinimalCodeConcept(**request.data)

        preferences = self._get_or_create_user_preferences(request.user, valueset)
        preferences.remove_favorite(code_obj.code)
        return Response({"message": f"Code {code_obj.code} removed from favorites"})

    @action(detail=True, methods=["POST"])
    def clear_favorites(self, request, *args, **kwargs):
        valueset = self.get_object()
        preference = UserValueSetPreference.objects.filter(
            user=request.user, valueset=valueset
        ).first()
        if preference:
            preference.clear_favorites()
        return Response({"message": "All favorite codes cleared"})

    @action(detail=True, methods=["GET"])
    def favorites(self, request, *args, **kwargs):
        valueset = self.get_object()
        preferences = UserValueSetPreference.objects.filter(
            user=request.user, valueset=valueset
        ).first()
        return Response(preferences.get_favorites() if preferences else [])

    @action(detail=True, methods=["POST"])
    def add_recent_view(self, request, *args, **kwargs):
        valueset = self.get_object()
        code_obj = MinimalCodeConcept(**request.data)

        preferences = self._get_or_create_user_preferences(request.user, valueset)
        preferences.add_recent_view(code_obj.model_dump())
        return Response({"message": f"Code {code_obj.code} added to recent views"})

    @action(detail=True, methods=["GET"])
    def recent_views(self, request, *args, **kwargs):
        valueset = self.get_object()
        preferences = UserValueSetPreference.objects.filter(
            user=request.user, valueset=valueset
        ).first()
        return Response(preferences.get_recent_views() if preferences else [])

    @action(detail=True, methods=["POST"])
    def clear_recent_views(self, request, *args, **kwargs):
        valueset = self.get_object()
        preference = UserValueSetPreference.objects.filter(
            user=request.user, valueset=valueset
        ).first()
        if preference:
            preference.clear_recent_views()
        return Response({"message": "All recent views cleared"})
