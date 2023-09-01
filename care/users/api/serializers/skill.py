from rest_framework.serializers import CharField, ModelSerializer, UUIDField

from care.users.models import Skill, UserSkill


class SkillSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)

    class Meta:
        model = Skill
        fields = ("id", "name", "description")


class UserSkillSerializer(ModelSerializer):
    id = UUIDField(source="skill.external_id", read_only=True)
    name = CharField(source="skill.name", read_only=True)
    description = CharField(source="skill.description", read_only=True)

    class Meta:
        model = UserSkill
        fields = ("id", "name", "description")
