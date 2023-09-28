from django.db import models

from care.utils.models.base import BaseModel


class Goal(BaseModel):
    name = models.CharField(max_length=200)


class GoalEntry(BaseModel):
    goal = models.ForeignKey(
        Goal,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    date = models.DateField()
    visitors = models.IntegerField(null=True)
    events = models.IntegerField(null=True)


class GoalProperty(BaseModel):
    name = models.CharField(max_length=200)
    goal = models.ForeignKey(
        Goal,
        on_delete=models.CASCADE,
        related_name="properties",
    )


class GoalPropertyEntry(BaseModel):
    goal_entry = models.ForeignKey(
        GoalEntry,
        on_delete=models.PROTECT,
        related_name="properties",
    )
    goal_property = models.ForeignKey(
        GoalProperty,
        on_delete=models.PROTECT,
        related_name="entries",
    )
    value = models.CharField(max_length=200)
    visitors = models.IntegerField(null=True)
    events = models.IntegerField(null=True)
