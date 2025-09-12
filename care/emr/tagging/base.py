from django.db.models import Q
from rest_framework.exceptions import ValidationError

from care.emr.models.tag_config import TagConfig
from care.emr.resources.tag.config_spec import TagConfigReadSpec
from care.facility.models.facility import Facility
from care.utils.shortcuts import get_object_or_404


class BaseTagManager:
    def set_tag(self, resource_type, resource, tag_instance, user, facility=None):
        pass

    def set_tags(self, resource_type, resource, tag_instances, user, facility=None):
        for i in tag_instances:
            self.set_tag(resource_type, resource, i, user, facility)

    def render_tags(self, resource, *args, **kwargs):
        pass

    def unset_tag(self, resource, tag_instance, user):
        pass

    def unset_tags(self, resource, tag_instances, user):
        for i in tag_instances:
            self.unset_tag(resource, i, user)

    def get_tag_config_object(self, tag_id, facility=None):
        # TODO: Add cache
        return TagConfig.objects.filter(id=tag_id).first()

    def get_tag_from_external_id(self, external_id):
        return TagConfig.objects.filter(external_id=external_id).first()


class SingleFacilityTagManager(BaseTagManager):
    def get_resource_tag(self, resource):
        return resource.tags or []

    def get_tag_config_object(self, external_id, facility):
        return TagConfig.objects.filter(
            Q(facility=facility) | Q(facility__isnull=True), external_id=external_id
        ).first()

    def set_instance_tag(self, instance, tags):
        instance.tags = tags
        return ["tags"]

    def set_tag(self, resource_type, resource, tag_instance, user, facility=None):
        # AuthZ pending
        # Attain Tag lock for resource id
        tags = self.get_resource_tag(resource)
        tag_instance = self.get_tag_config_object(tag_instance, facility)
        if not tag_instance:
            return
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
        fields = self.set_instance_tag(resource, tags)
        resource.save(update_fields=fields)

    def unset_tag(self, resource, tag_instance, user):
        tags = self.get_resource_tag(resource)
        tag_instance = self.get_tag_from_external_id(tag_instance)
        if tag_instance.id not in tags:
            # TODO Standardise and use valueerror and reraise as validation error
            raise ValidationError("Tag not set")
        tags.remove(tag_instance.id)
        fields = self.set_instance_tag(resource, tags)
        resource.save(update_fields=fields)

    def render_tags(self, resource, *args, **kwargs):
        tags = self.get_resource_tag(resource)
        rendered_tags = []
        for tag in tags:
            tag_obj = TagConfig.objects.filter(id=tag).first()
            if tag_obj:
                rendered_tags.append(TagConfigReadSpec.serialize(tag_obj).to_json())
        return rendered_tags


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
        if isinstance(facility, str):
            facility = get_object_or_404(Facility, external_id=facility)
        self.facility = facility

    def get_resource_tag(self, resource):
        return (resource.facility_tags or {}).get(self.facility.id, [])

    def set_instance_tag(self, instance, tags):
        facility_tags = instance.facility_tags or {}
        facility_tags[self.facility.id] = tags
        instance.facility_tags = facility_tags
        return ["facility_tags"]

    def get_tag_config_object(self, external_id, facility=None):
        return TagConfig.objects.filter(
            external_id=external_id, facility=self.facility
        ).first()
