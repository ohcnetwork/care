from django.core.management import BaseCommand
from django.db import transaction

from care.security.models import PermissionModel, RoleModel, RolePermission
from care.security.permissions.base import PermissionController
from care.security.roles.role import RoleController
from care.utils.lock import Lock


class Command(BaseCommand):
    """
    This command syncs roles, permissions and role-permission mapping to the database.
    This command should be run after all deployments and plug changes.
    This command is idempotent, multiple instances running the same command is automatically blocked with redis.
    """

    help = "Syncs permissions and roles to database"

    def handle(self, *args, **options):
        permissions = PermissionController.get_permissions()
        roles = RoleController.get_roles()
        with transaction.atomic(), Lock("sync_permissions_roles", 900):
            # Create, update permissions and delete old permissions
            PermissionModel.objects.all().update(temp_deleted=True)
            for permission, metadata in permissions.items():
                permission_obj = PermissionModel.objects.filter(slug=permission).first()
                if not permission_obj:
                    permission_obj = PermissionModel(slug=permission)
                permission_obj.name = metadata.name
                permission_obj.description = metadata.description
                permission_obj.context = metadata.context.value
                permission_obj.temp_deleted = False
                permission_obj.save()
            PermissionModel.objects.filter(temp_deleted=True).delete()
            # Create, update roles and delete old roles
            RoleModel.objects.filter(is_system=True).update(temp_deleted=True)
            for role in roles:
                role_obj = RoleModel.objects.filter(name=role.name).first()
                if not role_obj:
                    role_obj = RoleModel(name=role.name)
                role_obj.description = role.description
                role_obj.is_system = True
                role_obj.temp_deleted = False
                role_obj.save()
            RoleModel.objects.filter(temp_deleted=True).delete()
            # Sync permissions to role
            RolePermission.objects.filter(role__is_system=True).update(
                temp_deleted=True
            )
            role_cache = {}
            for permission, metadata in permissions.items():
                permission_obj = PermissionModel.objects.filter(slug=permission).first()
                for role in metadata.roles:
                    if role.name not in role_cache:
                        role_cache[role.name] = RoleModel.objects.get(name=role.name)
                    obj = RolePermission.objects.filter(
                        role=role_cache[role.name], permission=permission_obj
                    ).first()
                    if not obj:
                        obj = RolePermission(
                            role=role_cache[role.name], permission=permission_obj
                        )
                    obj.temp_deleted = False
                    obj.save()
            RolePermission.objects.filter(temp_deleted=True).delete()
