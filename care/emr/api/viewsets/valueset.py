from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from pydantic import UUID4, BaseModel, Field
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from care.emr.api.viewsets.base import EMRModelViewSet
from care.emr.fhir.resources.code_concept import CodeConceptResource, MinimalCodeConcept
from care.emr.models.organization import FacilityOrganization
from care.emr.models.valueset import (
    RecentViewsManager,
    UserFacilityValueSetPreference,
    UserValueSetPreference,
    ValueSet,
    ValueSetFacilityOrganization,
)
from care.emr.resources.common.coding import Coding
from care.emr.resources.facility_organization.spec import FacilityOrganizationReadSpec
from care.emr.resources.valueset.spec import (
    ValueSetAuthContext,
    ValueSetCreateSpec,
    ValuesetDatabaseModel,
    ValueSetReadSpec,
    ValueSetSpec,
    ValueSetUpdateSpec,
)
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404


class ExpandRequest(BaseModel):
    search: str = ""
    count: int = Field(10, gt=0, lt=100)
    display_language: str = "en-gb"


class ExpandSlugRequest(BaseModel):
    slug: str
    facility: UUID4 | None = None
    search: str = ""
    count: int = Field(10, gt=0, lt=100)
    display_language: str = "en-gb"


class ValueSetSlugPreference(BaseModel):
    slug: str
    facility: UUID4


class ValueSetFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains")
    status = filters.CharFilter(field_name="status", lookup_expr="iexact")
    auth_context = filters.CharFilter(field_name="auth_context", lookup_expr="iexact")
    facility = filters.UUIDFilter(field_name="facility__external_id")


def get_closest_valueset(queryset, slug, user, facility=None):
    valuesets = queryset.filter(slug=slug)
    valueset = None
    if facility:
        preference = UserFacilityValueSetPreference.objects.filter(
            user=user,
            facility__external_id=facility,
            slug=slug,
        ).first()
        preferred_valueset = None
        if preference:
            preferred_valueset = valuesets.filter(id=preference.valueset.id).first()
        if preferred_valueset:
            valueset = preferred_valueset
        else:
            valuesets = valuesets.filter(
                Q(
                    auth_context=ValueSetAuthContext.facility,
                    facility__external_id=facility,
                )
                | Q(
                    auth_context=ValueSetAuthContext.instance,
                )
            )
    else:
        valuesets = valuesets.filter(
            auth_context=ValueSetAuthContext.instance,
        )
    if not valueset:
        for valueset_option in valuesets.order_by("auth_context"):
            valueset = valueset_option
            break
    if not valueset:
        raise ValidationError("No valueset found")
    return valueset


class ValueSetViewSet(EMRModelViewSet):
    database_model = ValueSet
    pydantic_model = ValueSetCreateSpec
    pydantic_update_model = ValueSetUpdateSpec
    pydantic_read_model = ValueSetReadSpec
    filterset_class = ValueSetFilter
    filter_backends = [DjangoFilterBackend]

    def authorize_create(self, instance):
        if (
            instance.auth_context == ValueSetAuthContext.instance
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied("You are not authorized to create a value set")
        if instance.auth_context == ValueSetAuthContext.facility:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_access_facility_valueset",
                self.request.user,
                facility,
                None,
                read_only=False,
            ):
                raise PermissionDenied("You are not authorized to create a value set")
        if instance.auth_context == ValueSetAuthContext.facility_organization:
            facility_organization = get_object_or_404(
                FacilityOrganization, external_id=instance.facility_organization
            )
            if not AuthorizationController.call(
                "can_access_facility_organization_valueset",
                self.request.user,
                facility_organization,
                read_only=False,
            ):
                raise PermissionDenied("You are not authorized to create a value set")
        if instance.auth_context == ValueSetAuthContext.user:
            facility = get_object_or_404(Facility, external_id=instance.facility)
            if not AuthorizationController.call(
                "can_access_user_valueset_in_faciltiy",
                self.request.user,
                facility,
                read_only=False,
            ):
                raise PermissionDenied("You are not authorized to create a value set")

        return super().authorize_create(instance)

    def authorize_update(self, request_obj, model_instance):
        if (
            model_instance.auth_context == ValueSetAuthContext.instance
            and not self.request.user.is_superuser
        ):
            raise PermissionDenied("You are not authorized to create a value set")
        if (
            model_instance.auth_context == ValueSetAuthContext.facility
            and not AuthorizationController.call(
                "can_access_facility_valueset",
                self.request.user,
                model_instance.facility,
                None,
                read_only=False,
            )
        ):
            raise PermissionDenied("You are not authorized to create a value set")
        if (
            model_instance.auth_context == ValueSetAuthContext.facility_organization
            and not AuthorizationController.call(
                "can_access_facility_organization_valueset",
                self.request.user,
                model_instance.facility_organization,
                read_only=False,
            )
        ):
            raise PermissionDenied("You are not authorized to create a value set")
        if (
            model_instance.auth_context == ValueSetAuthContext.user
            and not AuthorizationController.call(
                "can_access_user_valueset_in_faciltiy",
                self.request.user,
                model_instance.facility,
                read_only=False,
            )
        ):
            raise PermissionDenied("You are not authorized to create a value set")
        if (
            model_instance.auth_context == ValueSetAuthContext.user
            and model_instance.created_by != self.request.user
        ):
            raise PermissionDenied("Only the creator of the value set can update it")

    def authorize_destroy(self, instance):
        self.authorize_update(self.request, instance)

    def perform_update(self, instance):
        if instance.inherited:
            old_obj = ValuesetDatabaseModel.objects.get(id=instance.id)
            instance.slug = old_obj.slug
        return super().perform_update(instance)

    def get_queryset(self):
        queryset = super().get_queryset()
        return AuthorizationController.call(
            "get_filtered_valuesets", queryset, self.request.user
        )

    @action(detail=True, methods=["GET"])
    def get_facility_organizations(self, request, *args, **kwargs):
        valueset = self.get_object()
        if not valueset.auth_context == ValueSetAuthContext.facility:
            raise PermissionDenied(
                "Facility organizations can only be set for facility level questionnaires"
            )
        self.authorize_update(None, valueset)
        questionnaire_organizations = ValueSetFacilityOrganization.objects.filter(
            valueset=valueset
        ).select_related("organization")
        organizations_serialized = [
            FacilityOrganizationReadSpec.serialize(obj.organization).to_json()
            for obj in questionnaire_organizations
        ]
        return Response(
            {
                "count": len(organizations_serialized),
                "results": organizations_serialized,
            }
        )

    class ValueSetFacilityOrganizationUpdateSchema(BaseModel):
        facility_organizations: list[UUID4]

    @extend_schema(request=ValueSetFacilityOrganizationUpdateSchema)
    @action(detail=True, methods=["POST"])
    def set_facility_organizations(self, request, *args, **kwargs):
        valueset = self.get_object()
        if not valueset.auth_context == ValueSetAuthContext.facility:
            raise PermissionDenied(
                "Facility organizations can only be set for facility level questionnaires"
            )
        self.authorize_update(None, valueset)
        request_params = self.ValueSetFacilityOrganizationUpdateSchema(**request.data)
        with transaction.atomic():
            ValueSetFacilityOrganization.objects.filter(valueset=valueset).delete()
            for org in request_params.facility_organizations:
                organization = get_object_or_404(
                    FacilityOrganization.objects.only("id"),
                    external_id=org,
                    facility=valueset.facility,
                )
                ValueSetFacilityOrganization.objects.create(
                    valueset=valueset, organization=organization
                )
            valueset.sync_facility_org_cache()
        return Response({})

    def get_recent_view_cache_key(self, valueset_uuid, user_id):
        return f"user_valueset_code_prefs:{valueset_uuid}:{user_id}:recent_views"

    def get_favourites_cache_key(self, valueset_uuid, user_id):
        return f"user_valueset_code_prefs:{valueset_uuid}:{user_id}:favourites"

    @extend_schema(
        request=ValueSetSlugPreference, responses={200: None}, methods=["POST"]
    )
    @action(detail=True, methods=["POST"])
    def set_slug_preference(self, request, *args, **kwargs):
        request_data = ValueSetSlugPreference(**request.data)
        obj = self.get_object()
        facility = get_object_or_404(Facility, external_id=request_data.facility)
        if obj.facility and obj.facility != facility:
            raise ValidationError(
                "Cannot set preference for different facility's valueset"
            )
        preference = UserFacilityValueSetPreference.objects.filter(
            user=request.user,
            facility=facility,
            slug=request_data.slug,
        ).first()
        if not preference:
            preference = UserFacilityValueSetPreference(
                user=request.user,
                facility=facility,
                slug=request_data.slug,
                valueset=obj,
            )
        else:
            preference.valueset = obj
        preference.save()
        return Response({})

    @extend_schema(request=ExpandRequest, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def expand(self, request, *args, **kwargs):
        request_params = ExpandRequest(**request.data).model_dump()
        results = self.get_object().search(**request_params)
        return Response({"results": [result.model_dump() for result in results]})

    @extend_schema(request=ExpandSlugRequest, responses={200: None}, methods=["POST"])
    @action(detail=False, methods=["POST"])
    def expand_slug(self, request, *args, **kwargs):
        request_data = ExpandSlugRequest(**request.data)
        request_params = request_data.model_dump(exclude={"slug", "facility"})

        valuesets = self.get_queryset().filter(slug=request_data.slug)
        valueset = get_closest_valueset(
            valuesets, request_data.slug, request.user, facility=request_data.facility
        )
        results = valueset.search(**request_params)
        return Response(
            {
                "valueset": ValueSetReadSpec.serialize(valueset).to_json(),
                "results": [result.model_dump() for result in results],
            }
        )

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

    @action(detail=True, methods=["GET"])
    def favourites(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_favourites_cache_key(valueset_uuid, user_id)
        favs = cache.get(cache_key)
        if favs is None:
            try:
                pref = UserValueSetPreference.objects.get(
                    user=request.user, valueset=self.get_object()
                )
                favs = pref.favorite_codes
            except UserValueSetPreference.DoesNotExist:
                favs = []
            cache.set(cache_key, favs)
        return Response(favs)

    @action(detail=False, methods=["GET"])
    def favourites_by_slug(self, request, *args, **kwargs):
        facility = request.GET.get("facility")
        closest_valueset = get_closest_valueset(
            self.get_queryset(),
            request.GET.get("slug"),
            request.user,
            facility=facility,
        )
        valueset_uuid = str(closest_valueset.external_id)
        user_id = request.user.external_id
        cache_key = self.get_favourites_cache_key(valueset_uuid, user_id)
        favs = cache.get(cache_key)
        if favs is None:
            try:
                pref = UserValueSetPreference.objects.get(
                    user=request.user, valueset=closest_valueset
                )
                favs = pref.favorite_codes
            except UserValueSetPreference.DoesNotExist:
                favs = []
            cache.set(cache_key, favs)
        return Response(favs)

    @action(detail=True, methods=["POST"])
    def add_favourite(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user = request.user
        cache_key = self.get_favourites_cache_key(valueset_uuid, user.external_id)
        code_obj = MinimalCodeConcept(**request.data)

        valueset = self.get_object()
        if not valueset.lookup(code_obj):
            raise ValidationError("Invalid code value")

        pref, _ = UserValueSetPreference.objects.get_or_create(
            user=user, valueset=valueset, defaults={"favorite_codes": []}
        )
        favs = pref.favorite_codes
        if not any(fav.get("code") == code_obj.code for fav in favs):
            favs.append(code_obj.model_dump())
            pref.favorite_codes = favs
            pref.save(update_fields=["favorite_codes", "modified_date"])
            cache.set(cache_key, favs)
            message = f"Code {code_obj.code} added to favourites"
        else:
            message = f"Code {code_obj.code} already exists in favourites"
        return Response({"message": message})

    @action(detail=True, methods=["POST"])
    def remove_favourite(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user = request.user
        cache_key = self.get_favourites_cache_key(valueset_uuid, user.external_id)
        code_obj = MinimalCodeConcept(**request.data)

        valueset = self.get_object()

        try:
            pref = UserValueSetPreference.objects.get(user=user, valueset=valueset)
            favs = pref.favorite_codes
            new_favs = [fav for fav in favs if fav.get("code") != code_obj.code]
            pref.favorite_codes = new_favs
            pref.save(update_fields=["favorite_codes", "modified_date"])
            cache.set(cache_key, new_favs)
            message = f"Code {code_obj.code} removed from favourites"
        except UserValueSetPreference.DoesNotExist:
            message = "No favourites found to remove from"
        return Response({"message": message})

    @action(detail=True, methods=["POST"])
    def clear_favourites(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user = request.user
        cache_key = self.get_favourites_cache_key(valueset_uuid, user.external_id)
        try:
            pref = UserValueSetPreference.objects.get(
                user=user, valueset=self.get_object()
            )
            pref.favorite_codes = []
            pref.save(update_fields=["favorite_codes", "modified_date"])
            cache.delete(cache_key)
            message = "All favourites cleared"
        except UserValueSetPreference.DoesNotExist:
            message = "No favourites found"
        return Response({"message": message})

    @extend_schema(request=MinimalCodeConcept, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def add_recent_view(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_recent_view_cache_key(valueset_uuid, user_id)
        code_obj = MinimalCodeConcept(**request.data)
        valueset = self.get_object()
        if not valueset.lookup(code_obj):
            raise ValidationError("Invalid code value")
        RecentViewsManager.add_recent_view(cache_key, code_obj.model_dump())
        return Response({"message": f"Code {code_obj.code} added to recent views"})

    @extend_schema(request=MinimalCodeConcept, responses={200: None}, methods=["POST"])
    @action(detail=True, methods=["POST"])
    def remove_recent_view(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_recent_view_cache_key(valueset_uuid, user_id)
        code_obj = MinimalCodeConcept(**request.data)
        RecentViewsManager.remove_recent_view(cache_key, code_obj.model_dump())
        return Response({"message": f"Code {code_obj.code} removed from recent views"})

    @action(detail=True, methods=["GET"])
    def recent_views(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_recent_view_cache_key(valueset_uuid, user_id)
        return Response(RecentViewsManager.get_recent_views(cache_key))

    @action(detail=False, methods=["GET"])
    def recent_views_by_slug(self, request, *args, **kwargs):
        facility = request.GET.get("facility")
        closest_valueset = get_closest_valueset(
            self.get_queryset(),
            request.GET.get("slug"),
            request.user,
            facility=facility,
        )
        valueset_uuid = str(closest_valueset.external_id)
        user_id = request.user.external_id
        cache_key = self.get_recent_view_cache_key(valueset_uuid, user_id)
        return Response(RecentViewsManager.get_recent_views(cache_key))

    @action(detail=True, methods=["POST"])
    def clear_recent_views(self, request, *args, **kwargs):
        valueset_uuid = kwargs.get(self.lookup_field)
        user_id = request.user.external_id
        cache_key = self.get_recent_view_cache_key(valueset_uuid, user_id)
        RecentViewsManager.clear_recent_views(cache_key)
        return Response({"message": "All recent views cleared"})
