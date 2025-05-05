from datetime import datetime, timedelta

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Max
from django.utils import timezone

from care.emr.models import EMRBaseModel, Encounter, FacilityOrganization
from config.celery_app import app


class FacilityLocation(EMRBaseModel):
    status = models.CharField(max_length=255)
    operational_status = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255)
    mode = models.CharField(max_length=255)
    location_type = models.JSONField(default=dict, null=True, blank=True)
    form = models.CharField(max_length=255)
    facility_organization_cache = ArrayField(models.IntegerField(), default=list)
    facility = models.ForeignKey("facility.Facility", on_delete=models.PROTECT)
    parent = models.ForeignKey(
        "emr.FacilityLocation", on_delete=models.SET_NULL, null=True, blank=True
    )
    has_children = models.BooleanField(default=False)
    level_cache = models.IntegerField(default=0)
    parent_cache = ArrayField(models.IntegerField(), default=list)
    metadata = models.JSONField(default=dict)
    cached_parent_json = models.JSONField(default=dict)
    root_location = models.ForeignKey(
        "self", on_delete=models.CASCADE, related_name="root", null=True, blank=True
    )
    current_encounter = models.ForeignKey(
        Encounter, on_delete=models.SET_NULL, null=True, blank=True, default=None
    )  # Populated from FacilityLocationEncounter
    sort_index = models.IntegerField(default=0)

    cache_expiry_days = 15

    def get_parent_json(self):
        from care.emr.resources.location.spec import FacilityLocationListSpec

        if self.parent_id:
            if self.cached_parent_json and timezone.now() < datetime.fromisoformat(
                self.cached_parent_json["cache_expiry"]
            ):
                return self.cached_parent_json
            self.parent.get_parent_json()
            temp_data = FacilityLocationListSpec.serialize(self.parent).to_json()
            temp_data["cache_expiry"] = str(
                timezone.now() + timedelta(days=self.cache_expiry_days)
            )
            self.cached_parent_json = temp_data
            super().save(update_fields=["cached_parent_json"])
            return self.cached_parent_json
        return {}

    @classmethod
    def validate_uniqueness(cls, queryset, pydantic_instance, model_instance):
        if model_instance:
            name = model_instance.name
            level_cache = model_instance.level_cache
            root_location = model_instance.root_location
            queryset = queryset.exclude(id=model_instance.id)
        else:
            name = pydantic_instance.name
            if pydantic_instance.parent:
                parent = cls.objects.get(external_id=pydantic_instance.parent)
                level_cache = parent.level_cache + 1
                root_location = parent.root_location
                if not root_location:
                    root_location = parent
            else:
                level_cache = 0
                root_location = None
        if root_location:
            queryset = queryset.filter(root_location=root_location)
        else:
            queryset = queryset.filter(root_location__isnull=True)
        queryset = queryset.filter(level_cache=level_cache, name=name)
        return queryset.exists()

    def sync_organization_cache(self):
        orgs = set()
        if self.parent:
            orgs = orgs.union(set(self.parent.facility_organization_cache))
        for (
            facility_location_organization
        ) in FacilityLocationOrganization.objects.filter(location=self):
            orgs = orgs.union(
                {
                    *facility_location_organization.organization.parent_cache,
                    facility_location_organization.organization.id,
                }
            )

        facility_root_org = FacilityOrganization.objects.filter(
            org_type="root", facility=self.facility
        ).first()
        if facility_root_org:
            orgs = orgs.union({facility_root_org.id})

        self.facility_organization_cache = list(orgs)
        super().save(update_fields=["facility_organization_cache"])

    def save(self, *args, **kwargs):
        if not self.id:
            if self.parent:
                self.level_cache = self.parent.level_cache + 1
                if self.parent.root_location is None:
                    self.root_location = self.parent
                else:
                    self.root_location = self.parent.root_location
                if not self.parent.has_children:
                    self.parent.has_children = True
                    self.parent.save(update_fields=["has_children"])
        else:
            self.cached_parent_json = {}
        if not self.sort_index:
            self.sort_index = (
                FacilityLocation.objects.filter(parent=self.parent).aggregate(
                    Max("sort_index", default=0)
                )["sort_index__max"]
                + 1
            )
        super().save(*args, **kwargs)
        self.sync_organization_cache()

    def cascade_changes(self):
        handle_cascade.delay(self.id)


class FacilityLocationOrganization(EMRBaseModel):
    """
    This relation denotes which organization can access a given Facility Location
    """

    location = models.ForeignKey(FacilityLocation, on_delete=models.CASCADE)
    organization = models.ForeignKey(
        "emr.FacilityOrganization", on_delete=models.CASCADE
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.location.save()
        self.location.cascade_changes()


class FacilityLocationEncounter(EMRBaseModel):
    """
    This relation denotes how a bed was associated to an encounter
    """

    status = models.CharField(max_length=25)
    location = models.ForeignKey(FacilityLocation, on_delete=models.CASCADE)
    encounter = models.ForeignKey(Encounter, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField(default=None, null=True, blank=True)


@app.task
def handle_cascade(base_location):
    """
    Cascade changes to a location organization to all its children
    """

    for child in FacilityLocation.objects.filter(parent_id=base_location):
        child.save(update_fields=["cached_parent_json"])
        handle_cascade(child)
