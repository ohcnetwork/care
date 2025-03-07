from django.contrib.contenttypes.models import ContentType
from django.db import models


class MigrationTracking(models.Model):
    """
    Model to track the migrations that have been run on the database.
    """

    old_model = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="old_model"
    )
    old_model_obj_id = models.BigIntegerField()
    new_model = models.ForeignKey(
        ContentType, on_delete=models.CASCADE, related_name="new_model"
    )
    new_model_obj_id = models.BigIntegerField()
    field = models.CharField(max_length=255)
    data = models.TimeField()

    def __str__(self):
        """
        Return a string representation of the migration tracking instance.
        
        This method returns a formatted string that shows the old model and its ID, the new model,
        and the specific field that was migrated.
        """
        return f"{self.old_model}({self.old_model_obj_id}) -> {self.new_model} : {self.field}"
