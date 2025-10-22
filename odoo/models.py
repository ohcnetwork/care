from django.conf import settings
from django.db import models


class UserOdooAgent(models.Model):
    """
    Model to store the mapping between Care User and Odoo Agent.
    This is a one-to-one relationship between User and Odoo Agent.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="odoo_agent",
        help_text="The Care user associated with this Odoo agent",
    )
    odoo_agent_id = models.IntegerField(help_text="The ID of the agent in Odoo system")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Odoo Agent"
        verbose_name_plural = "User Odoo Agents"
        db_table = "odoo_user_odoo_agent"

    def __str__(self):
        return f"Odoo Agent for {self.user.get_full_name()} (ID: {self.odoo_agent_id})"
