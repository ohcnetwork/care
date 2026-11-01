from datetime import datetime, timedelta
from uuid import UUID

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from care.emr.models.tag_config import TagConfig, TagDeleteRequest
from care.emr.resources.base import model_from_cache
from care.emr.resources.tag.config_spec import TagResource, tag_resource_to_model
from care.facility.models.facility import Facility
from care.security.authorization.base import AuthorizationController
from care.utils.shortcuts import get_object_or_404
from care.utils.time_util import care_now


class BaseTagManager:
    def lock_resource(self, resource):
        # Row locks belong to the outer transaction and can be acquired again
        # within that transaction; commit and rollback release them automatically.
        return type(resource).objects.select_for_update().get(pk=resource.pk)

    def lock_set_tag(self, resource_type, resource, tag_instance, user, facility=None):
        with transaction.atomic():
            self.lock_resource(resource)
            self.set_tag(resource_type, resource, tag_instance, user, facility)

    def set_tag(self, resource_type, resource, tag_instance, user, facility=None):
        pass

    def set_tags(self, resource_type, resource, tag_instances, user, facility=None):
        with transaction.atomic():
            self.lock_resource(resource)
            for i in tag_instances:
                self.set_tag(resource_type, resource, i, user, facility)

    def render_tags(self, resource, *args, **kwargs):
        pass

    def unset_tag(self, resource_type, resource, tag_instance, user):
        pass

    def unset_tags(self, resource_type, resource, tag_instances, user):
        with transaction.atomic():
            self.lock_resource(resource)
            for i in tag_instances:
                self.unset_tag(resource_type, resource, i, user)

    def get_tag_config_object(self, tag_id, facility=None):
        # TODO: Add cache
        return TagConfig.objects.filter(id=tag_id).first()

    def get_tag_from_external_id(self, external_id):
        return TagConfig.objects.filter(external_id=external_id).first()

    def set_expiry_data(self, resource, instance, expiry):
        # TODO Lock Object
        tag_id = str(instance.id)
        if tag_id not in resource.tags_data:
            resource.tags_data[tag_id] = {}
        resource.tags_data[tag_id]["expiry"] = expiry

    def remove_expiry_data(self, resource, instance):
        # TODO Lock Object
        tag_id = str(instance.id)
        if tag_id in resource.tags_data:
            del resource.tags_data[tag_id]

    def clean_expired_tags(self, resource):
        pass


def calculate_offset(offset):
    return care_now() + timedelta(**offset)


class SingleFacilityTagManager(BaseTagManager):
    def get_resource_tag(self, resource):
        return resource.tags or []

    def get_tag_config_object(self, tag_id, facility):
        return TagConfig.objects.filter(
            Q(facility=facility) | Q(facility__isnull=True),
            external_id=tag_id,
        ).first()

    def set_instance_tag(self, instance, tags):
        instance.tags = tags
        return ["tags"]

    def set_tag(self, resource_type, resource, tag_request, user, facility=None):
        resource.refresh_from_db()
        tags = self.get_resource_tag(resource)
        tag_instance = self.get_tag_config_object(tag_request.tag, facility)
        if not tag_instance:
            return

        if not AuthorizationController.call("can_apply_tag_config", user, tag_instance):
            error_msg = (
                f"You do not have permission to apply tag '{tag_instance.display}'"
            )
            raise PermissionDenied(error_msg)
        if tag_instance.id in tags:
            raise ValidationError("Tag already set")
        if tag_instance.resource != resource_type:
            raise ValidationError("Tag resource does not match resource type")
        if (
            tag_instance.root_tag_config
            and TagConfig.objects.filter(
                id__in=tags, root_tag_config=tag_instance.root_tag_config
            ).exists()
        ):
            raise ValidationError("Tag Parent is already set")
        tags.append(tag_instance.id)
        expiry = None
        if tag_instance.expiry_metadata:
            if tag_instance.expiry_metadata.get(
                "autoset_expiry"
            ) and tag_instance.expiry_metadata.get("expiry_offset"):
                expiry = calculate_offset(
                    tag_instance.expiry_metadata.get("expiry_offset")
                )

            if (
                tag_instance.expiry_metadata.get("modification_allowed")
                and tag_request.expiry_offset
            ):
                expiry = calculate_offset(
                    tag_request.expiry_offset.model_dump(mode="json")
                )

        fields = self.set_instance_tag(resource, tags)
        if expiry:
            self.set_expiry_data(resource, tag_instance, str(expiry))
            fields.append("tags_data")
            TagDeleteRequest.create_delete_request(
                resource_type, resource.id, tag_instance, expiry
            )
        resource.save(update_fields=fields)

    def unset_tag(self, resource_type, resource, tag_request, user):
        resource.refresh_from_db()
        tags = self.get_resource_tag(resource)
        tag_instance = self.get_tag_from_external_id(tag_request.tag)

        if not AuthorizationController.call("can_apply_tag_config", user, tag_instance):
            error_msg = (
                f"You do not have permission to remove tag '{tag_instance.display}'"
            )
            raise PermissionDenied(error_msg)

        if tag_instance.id not in tags:
            # TODO Standardise and use valueerror and reraise as validation error
            raise ValidationError("Tag not set")
        tags.remove(tag_instance.id)

        fields = self.set_instance_tag(resource, tags)
        fields.append("tags_data")
        self.remove_expiry_data(resource, tag_instance)
        resource.save(update_fields=fields)

    def render_tags(self, resource, *args, **kwargs):
        from care.emr.resources.tag.config_spec import TagConfigReadSpec

        tags_data = getattr(resource, "tags_data", {})  # TODO Move out
        tags = self.get_resource_tag(resource)
        rendered_tags = []
        for tag in tags:
            cached_tag = model_from_cache(TagConfigReadSpec, id=tag)
            if not cached_tag:
                continue
            tag_id = str(tag)
            if tag_id in tags_data:
                expiry = tags_data[tag_id]["expiry"]
                cached_tag["expiry"] = expiry
                if care_now() > datetime.fromisoformat(expiry):
                    cached_tag["expired"] = True
                    handle_expired_tag.delay(cached_tag["resource"], resource.id)
            rendered_tags.append(cached_tag)
        return rendered_tags

    def clean_expired_tags(self, resource):
        tags = self.get_resource_tag(resource)
        tags_data = getattr(resource, "tags_data", {})  # TODO Move out
        del_list = []
        for tag in tags:
            tag_id = str(tag)
            if tag_id in tags_data:
                expiry = tags_data[tag_id]["expiry"]
                if care_now() > datetime.fromisoformat(expiry):
                    del_list.append(tag_id)
        for tag_id in del_list:
            tags.remove(int(tag_id))
            del tags_data[tag_id]
        self.set_instance_tag(resource, tags)
        resource.tags_data = tags_data
        return resource


class PatientInstanceTagManager(SingleFacilityTagManager):
    def get_resource_tag(self, resource):
        return resource.instance_tags or []

    def set_instance_tag(self, instance, tags):
        instance.instance_tags = tags
        return ["instance_tags"]

    def get_tag_config_object(self, external_id, facility=None):
        return TagConfig.objects.filter(
            external_id=external_id, facility__isnull=True
        ).first()


class PatientFacilityTagManager(SingleFacilityTagManager):
    def __init__(self, facility) -> None:
        if isinstance(facility, (str, UUID)):
            facility = get_object_or_404(Facility, external_id=facility)
        self.facility = facility

    def get_resource_tag(self, resource):
        return (resource.facility_tags or {}).get(str(self.facility.id), [])

    @classmethod
    def get_all_facilities(cls, resource):
        return list((resource.facility_tags or {}).keys())

    def set_instance_tag(self, instance, tags):
        facility_tags = instance.facility_tags or {}
        facility_tags[self.facility.id] = tags
        instance.facility_tags = facility_tags
        return ["facility_tags"]

    def get_tag_config_object(self, external_id, facility=None):
        return TagConfig.objects.filter(
            external_id=external_id, facility=self.facility
        ).first()

    @classmethod
    def clean_expired_tags(cls, resource):
        tags_data = resource.tags_data
        for facility in cls.get_all_facilities(resource):
            facility = Facility.objects.filter(id=facility).first()
            if not facility:
                continue
            manager = cls(facility)
            tags = manager.get_resource_tag(resource)
            del_list = []
            for tag in tags:
                tag_id = str(tag)
                if tag_id in tags_data:
                    expiry = tags_data[tag_id]["expiry"]
                    if care_now() > datetime.fromisoformat(expiry):
                        del_list.append(tag_id)
            for tag_id in del_list:
                tags.remove(int(tag_id))
                del tags_data[tag_id]
            manager.set_instance_tag(resource, tags)
        resource.tags_data = tags_data
        return resource


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
)
def autohandle_expired_tasks():
    resources_to_evaluate = TagDeleteRequest.objects.filter(trigger_at__lte=care_now())
    for request in resources_to_evaluate:
        handle_expired_tag.delay(request.resource_type, request.resource_id)
        request.delete()


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3},
)
def handle_expired_tag(resource_type: TagResource, resource_id):
    with transaction.atomic():
        model = tag_resource_to_model(resource_type)
        resource = model.objects.select_for_update().get(id=resource_id)
        if resource_type == TagResource.patient.value:
            PatientInstanceTagManager().clean_expired_tags(resource=resource)
            PatientFacilityTagManager.clean_expired_tags(resource=resource)
            fields = ["instance_tags", "facility_tags", "tags_data"]
        else:
            SingleFacilityTagManager().clean_expired_tags(resource=resource)
            fields = ["tags", "tags_data"]
        resource.save(update_fields=fields)
