from care.emr.models.encounter import Encounter
from care.emr.reports.context_builder.base import Field, QuerysetContextBuilder
from care.emr.reports.context_builder.registry import contex_builder_registry
from care.users.models import User


# Todo: Need to rewrite it, it's a special case , maybe another builder subclass will be required
class CareTeamContextBuilder(QuerysetContextBuilder):
    model = User
    base_filters = {}
    allowed_filters = ["user_type"]

    fields = [
        Field(
            key="name",
            display="Team Member Name",
            mapping=lambda u: u.get_display_name(),
            preview_value="Dr. Rajesh Kumar",
            description="Full name of the care team member",
        ),
        Field(
            key="role",
            display="Role",
            mapping=lambda u: "",  # Will be populated from role_map in build_list_context
            preview_value="Primary Physician",
            description="Role of the team member in patient care",
        ),
    ]

    @classmethod
    def get_queryset(cls, ctx: dict):
        """Get care team members from encounter's care_team field"""
        encounter_id = ctx.get("encounter_id")
        # Todo: raise error if encounter_id is not present in ctx
        # Todo: raise error if encounter not found
        encounter = Encounter.objects.get(external_id=encounter_id)

        user_ids = [
            member.get("user_id")
            for member in encounter.care_team
            if member.get("user_id")
        ]

        if not user_ids:
            return cls.model.objects.none()

        queryset = cls.model.objects.filter(id__in=user_ids)

        if cls.base_filters:
            queryset = queryset.filter(**cls.base_filters)

        return queryset

    @classmethod
    def build_list_context(
        cls,
        ctx: dict,
        filters: dict | None = None,
        limit: int | None = None,
        requested_fields: list[str] | None = None,
    ):
        """
        Override to handle role mapping from encounter.care_team
        """
        # Get encounter and build role map
        encounter = ctx.get("encounter")
        if not encounter:
            encounter_id = ctx.get("encounter_id")
            if encounter_id:
                encounter = Encounter.objects.get(external_id=encounter_id)

        role_map = {}
        if encounter and hasattr(encounter, "care_team") and encounter.care_team:
            role_map = {
                member.get("user_id"): member.get("role", {}).get("display", "Unknown")
                for member in encounter.care_team
                if member.get("user_id") and member.get("role")
            }

        # Get base queryset
        queryset = cls.get_queryset(ctx)

        # Apply additional filters if provided
        if filters:
            queryset = queryset.filter(**filters)

        # Apply limit using Django queryset slicing (executes at database level)
        if limit is not None and limit > 0:
            queryset = queryset[:limit]

        # Build context for each object with role mapping
        result = []
        for user in queryset:
            user_context = cls._build_context_from_object(user, requested_fields)
            # Override role field with value from role_map
            if "role" in user_context:
                user_context["role"] = role_map.get(user.id, "Unknown")
            result.append(user_context)

        return result

    @classmethod
    def get_display_name(cls):
        return "Care Team"

    @classmethod
    def get_description(cls):
        return "Healthcare professionals involved in patient care"


# Register the builder
contex_builder_registry.register("care_team", CareTeamContextBuilder)
