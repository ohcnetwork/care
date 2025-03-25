from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone
from django_filters import rest_framework as filters

from care.users.models import User


def remove_facility_user_cache(user_id):
    key = f"user_facilities:{user_id!s}"
    cache.delete(key)
    return True


def inverse_choices(choices):
    output = {}
    for choice in choices:
        output[choice[1]] = choice[0]
    return output


INVERSE_USER_TYPE = inverse_choices(User.TYPE_CHOICES)


class UserFilterSet(filters.FilterSet):
    id = filters.NumberFilter(field_name="id", lookup_expr="exact")
    first_name = filters.CharFilter(field_name="first_name", lookup_expr="icontains")
    last_name = filters.CharFilter(field_name="last_name", lookup_expr="icontains")
    username = filters.CharFilter(field_name="username", lookup_expr="icontains")
    phone_number = filters.CharFilter(
        field_name="phone_number", lookup_expr="icontains"
    )
    alt_phone_number = filters.CharFilter(
        field_name="alt_phone_number", lookup_expr="icontains"
    )
    last_login = filters.DateFromToRangeFilter(field_name="last_login")
    district_id = filters.NumberFilter(field_name="district_id", lookup_expr="exact")
    home_facility = filters.CharFilter(method="filter_home_facility")

    def filter_home_facility(self, queryset, name, value):
        if value == "NONE":
            return queryset.filter(home_facility__isnull=True)
        return queryset.filter(home_facility__external_id=value)

    last_active_days = filters.CharFilter(method="last_active_after")

    def get_user_type(
        self,
        queryset,
        field_name,
        value,
    ):
        if value and value in INVERSE_USER_TYPE:
            return queryset.filter(user_type=INVERSE_USER_TYPE[value])
        return queryset

    user_type = filters.CharFilter(method="get_user_type", field_name="user_type")

    def last_active_after(self, queryset, name, value):
        if value == "never":
            return queryset.filter(last_login__isnull=True)
        # convert days to date
        date = timezone.now() - timedelta(days=int(value))

        return queryset.filter(last_login__gte=date)


#
# class UserViewSet(
#     mixins.RetrieveModelMixin,
#     mixins.UpdateModelMixin,
#     mixins.ListModelMixin,
#     mixins.DestroyModelMixin,
#     GenericViewSet,
# ):
#     """
#     A viewset for viewing and manipulating user instances.
#     """
#
#     queryset = (
#         User.objects.filter(is_active=True, is_superuser=False)
#         .select_related("local_body", "district", "state", "home_facility")
#         .order_by(F("last_login").desc(nulls_last=True))
#         .annotate(
#             created_by_user=F("created_by__username"),
#         )
#     )
#     queryset = queryset.filter(Q(asset__isnull=True))
#     lookup_field = "username"
#     lookup_value_regex = "[^/]+"
#     permission_classes = (IsAuthenticated, DRYPermissions)
#     filter_backends = (
#         filters.DjangoFilterBackend,
#         rest_framework_filters.OrderingFilter,
#         drf_filters.SearchFilter,
#     )
#     filterset_class = UserFilterSet
#     ordering_fields = ["id", "date_joined", "last_login"]
#     search_fields = ["first_name", "last_name", "username"]
#
#     def get_queryset(self):
#         if self.request.user.is_superuser:
#             return super().get_queryset()
#         query = Q(id=self.request.user.id)
#         if self.request.user.user_type >= User.TYPE_VALUE_MAP["StateReadOnlyAdmin"]:
#             query |= Q(
#                 state=self.request.user.state,
#                 user_type__lte=User.TYPE_VALUE_MAP["StateAdmin"],
#                 is_superuser=False,
#             )
#         elif (
#             self.request.user.user_type >= User.TYPE_VALUE_MAP["DistrictReadOnlyAdmin"]
#         ):
#             query |= Q(
#                 district=self.request.user.district,
#                 user_type__lte=User.TYPE_VALUE_MAP["DistrictAdmin"],
#                 is_superuser=False,
#             )
#         else:
#             query |= Q(
#                 id__in=Subquery(
#                     FacilityUser.objects.filter(
#                         facility_id__in=get_accessible_facilities(self.request.user)
#                     ).values("user_id")
#                 ),
#                 user_type__lt=User.TYPE_VALUE_MAP["DistrictAdmin"],
#                 is_superuser=False,
#             )
#         return self.queryset.filter(query)
#
#     def get_object(self) -> User:
#         try:
#             if self.action == "retrieve":
#                 username = self.kwargs.get("username")
#                 return get_object_or_404(User, username=username)
#             return super().get_object()
#         except Http404 as e:
#             error = "User not found"
#             raise Http404(error) from e
#
#     def get_serializer_class(self):
#         if self.action == "list":
#             return UserListSerializer
#         if self.action == "add_user":
#             return UserCreateSerializer
#         if self.action == "profile_picture":
#             return UserImageUploadSerializer
#         return UserSerializer
#
#     @extend_schema(tags=["users"])
#     @action(detail=False, methods=["GET"])
#     def getcurrentuser(self, request):
#         return Response(
#             status=status.HTTP_200_OK,
#             data=UserSerializer(request.user, context={"request": request}).data,
#         )
#
#     def destroy(self, request, *args, **kwargs):
#         queryset = self.get_queryset()
#         username = kwargs["username"]
#         if request.user.is_superuser:
#             pass
#         elif request.user.user_type >= User.TYPE_VALUE_MAP["StateAdmin"]:
#             queryset = queryset.filter(
#                 state=request.user.state,
#                 user_type__lt=User.TYPE_VALUE_MAP["StateAdmin"],
#                 is_superuser=False,
#             )
#         elif request.user.user_type == User.TYPE_VALUE_MAP["DistrictAdmin"]:
#             queryset = queryset.filter(
#                 district=request.user.district,
#                 user_type__lt=User.TYPE_VALUE_MAP["DistrictAdmin"],
#                 is_superuser=False,
#             )
#         else:
#             return Response(
#                 status=status.HTTP_403_FORBIDDEN, data={"permission": "Denied"}
#             )
#         user = get_object_or_404(queryset.filter(username=username))
#         user.is_active = False
#         user.save(update_fields=["is_active"])
#         return Response(status=status.HTTP_204_NO_CONTENT)
#
#     @extend_schema(tags=["users"])
#     @action(detail=False, methods=["POST"])
#     def add_user(self, request, *args, **kwargs):
#         password = request.data.pop(
#             "password", User.objects.make_random_password(length=8)
#         )
#         serializer = UserCreateSerializer(
#             data={**request.data, "password": password},
#             context={"created_by": request.user},
#         )
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(status=status.HTTP_201_CREATED)
#
#     def has_facility_permission(self, user, facility):
#         return (
#             user.is_superuser
#             or (facility and user in facility.users.all())
#             or (
#                 user.user_type >= User.TYPE_VALUE_MAP["LocalBodyAdmin"]
#                 and (facility and user.local_body == facility.local_body)
#             )
#             or (
#                 user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]
#                 and (facility and user.district == facility.district)
#             )
#             or (
#                 user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]
#                 and (facility and user.state == facility.state)
#             )
#         )
#
#     def has_user_type_permission_elevation(self, init_user, dest_user):
#         return init_user.user_type >= dest_user.user_type
#
#     def check_facility_user_exists(self, user, facility):
#         return FacilityUser.objects.filter(facility=facility, user=user).exists()
#
#     @extend_schema(tags=["users"])
#     @action(detail=True, methods=["GET"], permission_classes=[IsAuthenticated])
#     def get_facilities(self, request, *args, **kwargs):
#         user = self.get_object()
#         queryset = Facility.objects.filter(users=user).select_related(
#             "local_body", "district", "state", "ward"
#         )
#         facilities = self.paginate_queryset(queryset)
#         facilities = FacilityBasicInfoSerializer(facilities, many=True)
#         return self.get_paginated_response(facilities.data)
#
#     @extend_schema(tags=["users"])
#     @action(detail=True, methods=["PUT"], permission_classes=[IsAuthenticated])
#     def add_facility(self, request, *args, **kwargs):
#         # Remove User Facility Cache
#         user = self.get_object()
#         remove_facility_user_cache(user.id)
#         # Cache Deleted
#         requesting_user = request.user
#         if "facility" not in request.data:
#             raise ValidationError({"facility": "required"})
#         facility = Facility.objects.filter(external_id=request.data["facility"]).first()
#         if not facility:
#             raise ValidationError({"facility": "Does not Exist"})
#         if not self.has_user_type_permission_elevation(requesting_user, user):
#             raise ValidationError({"facility": "cannot Access Higher Level User"})
#         if not self.has_facility_permission(requesting_user, facility):
#             raise ValidationError({"facility": "Facility Access not Present"})
#         if self.check_facility_user_exists(user, facility):
#             raise ValidationError(
#                 {"facility": "User Already has permission to this facility"}
#             )
#         FacilityUser(facility=facility, user=user, created_by=requesting_user).save()
#         return Response(status=status.HTTP_201_CREATED)
#
#     @extend_schema(tags=["users"])
#     @extend_schema(
#         request=None,
#         responses={204: "Deleted Successfully"},
#     )
#     @action(detail=True, methods=["DELETE"], permission_classes=[IsAuthenticated])
#     def clear_home_facility(self, request, *args, **kwargs):
#         user = self.get_object()
#         requesting_user = request.user
#
#         if not user.home_facility:
#             raise ValidationError({"home_facility": "No Home Facility Present"})
#         if (
#             requesting_user.id == user.id
#             and requesting_user.user_type == User.TYPE_VALUE_MAP["Nurse"]
#         ):
#             pass
#         elif (
#             requesting_user.user_type < User.TYPE_VALUE_MAP["DistrictAdmin"]
#             or requesting_user.user_type in User.READ_ONLY_TYPES
#         ):
#             raise ValidationError({"home_facility": "Insufficient Permissions"})
#
#         if not self.has_user_type_permission_elevation(requesting_user, user):
#             raise ValidationError({"home_facility": "Cannot Access Higher Level User"})
#
#         # ensure that district admin only able to delete in the same district
#         if (
#             requesting_user.user_type <= User.TYPE_VALUE_MAP["DistrictAdmin"]
#             and user.district_id != requesting_user.district_id
#         ):
#             raise ValidationError(
#                 {"facility": "Cannot unlink User's Home Facility from other district"}
#             )
#
#         user.home_facility = None
#         user.save(update_fields=["home_facility"])
#         return Response(status=status.HTTP_204_NO_CONTENT)
#
#     @extend_schema(tags=["users"])
#     @action(detail=True, methods=["DELETE"], permission_classes=[IsAuthenticated])
#     def delete_facility(self, request, *args, **kwargs):
#         # Remove User Facility Cache
#         user = self.get_object()
#         remove_facility_user_cache(user.id)
#         # Cache Deleted
#         requesting_user = request.user
#         if "facility" not in request.data:
#             raise ValidationError({"facility": "required"})
#         facility = Facility.objects.filter(external_id=request.data["facility"]).first()
#         if not facility:
#             raise ValidationError({"facility": "Does not Exist"})
#         if not self.has_user_type_permission_elevation(requesting_user, user):
#             raise ValidationError({"facility": "cannot Access Higher Level User"})
#         if not self.has_facility_permission(requesting_user, facility):
#             raise ValidationError({"facility": "Facility Access not Present"})
#         if not self.has_facility_permission(user, facility):
#             raise ValidationError(
#                 {"facility": "Intended User Does not have permission to this facility"}
#             )
#         if user.home_facility == facility:
#             raise ValidationError({"facility": "Cannot Delete User's Home Facility"})
#         FacilityUser.objects.filter(facility=facility, user=user).delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)
#
#     @extend_schema(tags=["users"])
#     @action(
#         detail=True,
#         methods=["PATCH", "GET"],
#         permission_classes=[IsAuthenticated],
#     )
#     def pnconfig(self, request, *args, **kwargs):
#         user = request.user
#         if request.method == "GET":
#             return Response(
#                 {
#                     "pf_endpoint": user.pf_endpoint,
#                     "pf_p256dh": user.pf_p256dh,
#                     "pf_auth": user.pf_auth,
#                 }
#             )
#         acceptable_fields = ["pf_endpoint", "pf_p256dh", "pf_auth"]
#         for field in acceptable_fields:
#             if field in request.data:
#                 setattr(user, field, request.data[field])
#         user.save()
#         return Response(status=status.HTTP_200_OK)
#
#     @extend_schema(tags=["users"])
#     @action(methods=["GET"], detail=True)
#     def check_availability(self, request, username):
#         """
#         Checks availability of username by getting as query, returns 200 if available, and 409 otherwise.
#         """
#         if User.check_username_exists(username):
#             return Response(status=status.HTTP_409_CONFLICT)
#         return Response(status=status.HTTP_200_OK)
#
#     def has_profile_image_write_permission(self, request, user):
#         return request.user.is_superuser or (user.id == request.user.id)
#
#     @extend_schema(tags=["users"])
#     @method_decorator(parser_classes([MultiPartParser]))
#     @action(detail=True, methods=["POST"], permission_classes=[IsAuthenticated])
#     def profile_picture(self, request, *args, **kwargs):
#         user = self.get_object()
#         if not self.has_profile_image_write_permission(request, user):
#             return Response(status=status.HTTP_403_FORBIDDEN)
#         serializer = self.get_serializer(user, data=request.data)
#         serializer.is_valid(raise_exception=True)
#         serializer.save()
#         return Response(status=status.HTTP_200_OK)
#
#     @extend_schema(tags=["users"])
#     @profile_picture.mapping.delete
#     def profile_picture_delete(self, request, *args, **kwargs):
#         user = self.get_object()
#         if not self.has_profile_image_write_permission(request, user):
#             return Response(status=status.HTTP_403_FORBIDDEN)
#         delete_cover_image(user.profile_picture_url, "avatars")
#         user.profile_picture_url = None
#         user.save()
#         return Response(status=status.HTTP_204_NO_CONTENT)
