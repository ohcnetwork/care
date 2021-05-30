import base64

from django.conf import settings
from django_filters import rest_framework as filters
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin, UpdateModelMixin
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from care.facility.api.serializers.notification import NotificationSerializer
from care.facility.models.notification import Notification


from care.utils.filters.choicefilter import CareChoiceFilter, inverse_choices

inverse_event_type_choices = inverse_choices(Notification.EventTypeChoices)
inverse_event_choices = inverse_choices(Notification.EventChoices)


class NotificationFilter(filters.FilterSet):
    event = CareChoiceFilter(choice_dict=inverse_event_choices)
    event_type = CareChoiceFilter(choice_dict=inverse_event_type_choices)


class NotificationViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = Notification.objects.all().select_related("intended_for", "caused_by").order_by("-created_date")
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "external_id"
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_class = NotificationFilter

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(intended_for=user)

    @action(detail=False, methods=["GET"], permission_classes=[IsAuthenticatedOrReadOnly])
    def public_key(self, request, *args, **kwargs):
        return Response({"public_key": base64.urlsafe_b64encode(str.encode(settings.VAPID_PUBLIC_KEY))})
