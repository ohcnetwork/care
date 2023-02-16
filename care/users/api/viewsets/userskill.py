from django.db.utils import IntegrityError
from rest_framework.exceptions import ValidationError
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from care.users.api.serializers.userskill import UserSkillSerializer
from care.users.models import User, UserSkill
from care.utils.queryset.user import get_users


class UserSkillViewSet(
    ModelViewSet,
    GenericViewSet,
):
    serializer_class = UserSkillSerializer
    queryset = UserSkill.objects.all()
    lookup_field = "external_id"

    def get_queryset(self):
        username = self.kwargs["users_username"]
        user = get_object_or_404(User, username=username)

        return self.queryset.filter(user=user)

    def perform_create(self, serializer):
        username = self.kwargs["users_username"]
        user = get_object_or_404(get_users(self.request.user).filter(username=username))
        try:
            serializer.save(user=user)
        except IntegrityError as e:
            raise ValidationError({"skill": "Already exists"}) from e
