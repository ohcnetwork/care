from django.core.validators import RegexValidator
from django.db import models
from django.db.models import QuerySet, signals


class SoftDeleteQuerySet(QuerySet):
    def delete(self):
        self.update(active=False)
        for obj in self:
            signals.post_delete.send(sender=obj.__class__, instance=obj)

    def hard_delete(self):
        return super(SoftDeleteQuerySet, self).delete()


class ActiveObjectsManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(active=True)

    def hard_delete(self):
        return self.get_queryset().hard_delete()


class SoftDeleteModel(models.Model):
    """
    Abstract generic model used to allow an object to be soft deleted instead removing it from db.
    """

    active = models.BooleanField(default=True)

    objects = ActiveObjectsManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None):
        """
        Method to soft delete an object
        """
        signals.pre_delete.send(sender=self.__class__, instance=self)
        # Don't use .save() otherwise it will trigger save signals
        self.__class__.all_objects.filter(id=self.id).update(active=False)
        signals.post_delete.send(sender=self.__class__, instance=self)

    def restore(self, using=None):
        """
        Method to restore soft deleted object.
        If needed, add required signals
        """
        self.active = True
        self.save()

    def hard_delete(self, using=None):
        super(SoftDeleteModel, self).delete(using)


class TimeStampModel(models.Model):
    """
    Abstract Generic model for updated_at and created_at field
    """

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta(object):
        abstract = True


class SoftDeleteTimeStampedModel(SoftDeleteModel, TimeStampModel):
    """
    TimeStamped and SoftDelete Model
    """

    class Meta(SoftDeleteModel.Meta, TimeStampModel.Meta):
        abstract = True


class OwnershipType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name}"


class AddressModel(models.Model):
    """
    Abstract model for Address fields
    """

    address = models.TextField()
    district = models.ForeignKey(
        "accounts.District", on_delete=models.PROTECT, null=True, blank=True
    )
    state = models.ForeignKey(
        "accounts.State", on_delete=models.PROTECT, null=True, blank=True
    )
    pincode = models.CharField(
        max_length=6, validators=[RegexValidator(r"^\d{1,6}$")], null=True, blank=True
    )

    class Meta(object):
        abstract = True
