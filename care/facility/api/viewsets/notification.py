from django.conf import settings
from django_filters import rest_framework as filters
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import CharField, UUIDField
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.notification import NotificationSerializer
from care.facility.models.notification import Notification
from care.users.models import User
from care.utils.filters.choicefilter import CareChoiceFilter, inverse_choices
from care.utils.notification_handler import NotificationGenerator
from care.utils.queryset.facility import get_facility_queryset

inverse_event_type_choices = inverse_choices(Notification.EventTypeChoices)
inverse_event_choices = inverse_choices(Notification.EventChoices)
medium_choices = inverse_choices(Notification.MediumChoices)


class NotificationFilter(filters.FilterSet):
    event = CareChoiceFilter(choice_dict=inverse_event_choices)
    event_type = CareChoiceFilter(choice_dict=inverse_event_type_choices)
    medium_sent = CareChoiceFilter(choice_dict=medium_choices)


class NotificationViewSet(
    RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet
):
    queryset = (
        Notification.objects.all()
        .select_related("intended_for", "caused_by")
        .order_by("-created_date")
    )
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = NotificationFilter

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(intended_for=user)

    @extend_schema(tags=["notification"])
    @action(
        detail=False, methods=["GET"], permission_classes=[IsAuthenticatedOrReadOnly]
    )
    def public_key(self, request, *args, **kwargs):
        return Response({"public_key": settings.VAPID_PUBLIC_KEY})

    @extend_schema(
        request=inline_serializer(
            "BoardMessageSerializer",
            fields={
                "facility": UUIDField(required=True),
                "message": CharField(required=True),
            },
        ),
        responses={204: "Notification Processed"},
        tags=["notification"],
    )
    @action(detail=False, methods=["POST"])
    def notify(self, request, *args, **kwargs):
        user = request.user
        if user.user_type < User.TYPE_VALUE_MAP["Doctor"]:
            raise PermissionDenied()
        if "facility" not in request.data or request.data["facility"] == "":
            raise ValidationError({"facility": "is required"})
        if "message" not in request.data or request.data["message"] == "":
            raise ValidationError({"message": "is required"})
        facilities = get_facility_queryset(user)
        facility = get_object_or_404(
            facilities.filter(external_id=request.data["facility"])
        )
        NotificationGenerator(
            event_type=Notification.EventType.CUSTOM_MESSAGE,
            event=Notification.Event.MESSAGE,
            caused_by=user,
            facility=facility,
            caused_object=user,
            message=request.data["message"],
        ).generate()
        return Response(status=status.HTTP_204_NO_CONTENT)
