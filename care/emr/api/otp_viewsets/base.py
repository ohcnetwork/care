from django.conf import settings


class QuerysetEnablerMixin:
    """
    Mixin to enable queryset filtering based on the presence of a filterset_class attribute.
    """

    def get_queryset(self):
        if not settings.OTP_QUERYSET_ENABLED:
            return self.database_model.objects.none()
        return super().get_queryset()
