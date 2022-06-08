from care.users.models import Skill
from rest_framework.serializers import UUIDField, ModelSerializer


class SkillSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Skill
        fields = ("id", "name", "description")

