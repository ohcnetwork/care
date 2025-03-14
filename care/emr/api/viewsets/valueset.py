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
            "favourites",
            "add_favourite",
            "remove_favourite",
            "clear_favourites",
            "recent_views",
            "add_recent_view",
            "remove_recent_view",
            "clear_recent_views",
        ]:
            return True
        # Only superusers have write permission over valuesets
        return request.user.is_superuser

    def get_queryset(self):
        return ValueSet.objects.all().select_related("created_by", "updated_by")

    def get_serializer_class(self):
        return ValueSetSpec

    def get_cache_key(self, valueset_id, user_id):
        return f"user_valueset_code_prefs:{valueset_id}:{user_id}:recent_views"

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
        Coding(**request.data)
        try:
            result = (
                CodeConceptResource()
                .filter(
                    code=request.data["code"],
                    system=request.data["system"],
                    property="*",
                )
                .get()
            )
        except ValueError:
            return Response(
                {"error": "No results found for the given system and code"}, status=404
            )
        return Response(result)

    def _get_or_create_user_preferences(self, user, valueset) -> UserValueSetPreference:
        return UserValueSetPreference.objects.get_or_create(
            user=user,
            valueset=valueset,
            defaults={"favorite_codes": []},
        )[0]

    @extend_schema(request=MinimalCodeConcept, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def add_favourite(self, request, *args, **kwargs):
        valueset = self.get_object()
        code_obj = MinimalCodeConcept(**request.data)

        # validate the code
        if not valueset.lookup(code_obj):
            raise ValidationError("Invalid value")

        preferences = self._get_or_create_user_preferences(request.user, valueset)

        if len(preferences.get_favourites()) >= preferences.MAX_FAVORITES:
            raise ValidationError("Maximum number of favorites reached (50)")

        preferences.add_favourite(code_obj.model_dump())
        valueset_id = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_cache_key(valueset_id, user_id)
        # Add to recent views as well
        UserValueSetPreference.add_recent_view(cache_key, code_obj.model_dump())
        return Response({"message": f"Code {code_obj.code} marked as favorite"})

    @action(detail=True, methods=["POST"])
    def remove_favourite(self, request, *args, **kwargs):
        valueset = self.get_object()
        code_obj = MinimalCodeConcept(**request.data)

        preferences = self._get_or_create_user_preferences(request.user, valueset)
        preferences.remove_favourite(code_obj.code)
        return Response({"message": f"Code {code_obj.code} removed from favorites"})

    @action(detail=True, methods=["POST"])
    def clear_favourites(self, request, *args, **kwargs):
        valueset = self.get_object()
        preference = UserValueSetPreference.objects.filter(
            user=request.user, valueset=valueset
        ).first()
        if preference:
            preference.clear_favourites()
        return Response({"message": "All favorite codes cleared"})

    @action(detail=True, methods=["GET"])
    def favourites(self, request, *args, **kwargs):
        valueset = self.get_object()
        preferences = UserValueSetPreference.objects.filter(
            user=request.user, valueset=valueset
        ).first()
        return Response(preferences.get_favourites() if preferences else [])

    @extend_schema(request=MinimalCodeConcept, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def add_recent_view(self, request, *args, **kwargs):
        valueset_id = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_cache_key(valueset_id, user_id)
        code_obj = MinimalCodeConcept(**request.data)
        UserValueSetPreference.add_recent_view(cache_key, code_obj.model_dump())
        return Response({"message": f"Code {code_obj.code} added to recent views"})

    @extend_schema(request=MinimalCodeConcept, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def remove_recent_view(self, request, *args, **kwargs):
        valueset_id = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_cache_key(valueset_id, user_id)
        code_obj = MinimalCodeConcept(**request.data)
        UserValueSetPreference.remove_recent_view(cache_key, code_obj.model_dump())
        return Response({"message": f"Code {code_obj.code} removed from recent views"})

    @action(detail=True, methods=["GET"])
    def recent_views(self, request, *args, **kwargs):
        valueset_id = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_cache_key(valueset_id, user_id)
        return Response(UserValueSetPreference.get_recent_views(cache_key))

    @action(detail=True, methods=["POST"])
    def clear_recent_views(self, request, *args, **kwargs):
        valueset_id = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_cache_key(valueset_id, user_id)
        UserValueSetPreference.clear_recent_views(cache_key)
        return Response({"message": "All recent views cleared"})
