from django.utils.deprecation import MiddlewareMixin

from care.parxio_core.models import Tenant
from care.parxio_core.tenant import clear_current_tenant, get_subdomain_from_request, set_current_tenant


class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        clear_current_tenant()
        subdomain = get_subdomain_from_request(request)
        request.current_tenant = None
        if not subdomain:
            return

        tenant = Tenant.objects.filter(subdomain=subdomain, is_active=True).first()
        request.current_tenant = tenant
        if tenant:
            set_current_tenant(tenant)

    def process_response(self, request, response):
        clear_current_tenant()
        return response

    def process_exception(self, request, exception):
        clear_current_tenant()
        return None
