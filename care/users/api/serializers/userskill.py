from care.users.models import Skill, UserSkill
from rest_framework.serializers import UUIDField, ModelSerializer
from care.users.api.serializers.skill import SkillSerializer
from care.utils.serializer.external_id_field import ExternalIdSerializerField


class UserSkillSerializer(ModelSerializer):
    id = UUIDField(source="external_id", read_only=True)
    skill = ExternalIdSerializerField(write_only=True, required=True, queryset=Skill.objects.all())
    skill_object = SkillSerializer(source="skill", read_only=True)

    class Meta:
        model = UserSkill
        fields = ("id", "skill", "skill_object")

