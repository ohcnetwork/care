from rest_framework import filters as drf_filters
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from care.users.api.serializers.userskill import UserSkillSerializer
from care.users.models import User, UserSkill
from care.utils.queryset.user import get_users

from django.db.utils import IntegrityError
from rest_framework.exceptions import ValidationError


class UserSkillViewSet(
    ModelViewSet, GenericViewSet,
):
    serializer_class = UserSkillSerializer
    queryset = UserSkill.objects.all()
    lookup_field = "external_id"

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset
        if user.is_superuser:
            pass
        elif user.user_type >= User.TYPE_VALUE_MAP["StateLabAdmin"]:
            queryset = queryset.filter(user__state=user.state)
        elif user.user_type >= User.TYPE_VALUE_MAP["DistrictLabAdmin"]:
            queryset = queryset.filter(user__district=user.district)
        else:
            queryset = queryset.filter(user=user)
        return queryset

    def perform_create(self, serializer):
        username = self.kwargs["users_username"]
        user = get_object_or_404(get_users(self.request.user).filter(username=username))
        try:
            serializer.save(user=user)
        except IntegrityError as e:
            raise ValidationError({"skill": "Already exists"}) from e

