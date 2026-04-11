from contextvars import ContextVar

from django.http import HttpRequest

_current_tenant = ContextVar("current_tenant", default=None)
_current_tenant_id = ContextVar("current_tenant_id", default=None)

RESERVED_SUBDOMAINS = {"app", "www", "api", "admin", "localhost"}


def set_current_tenant(tenant):
    _current_tenant.set(tenant)
    _current_tenant_id.set(getattr(tenant, "id", None))


def clear_current_tenant():
    _current_tenant.set(None)
    _current_tenant_id.set(None)


def get_current_tenant():
    return _current_tenant.get()


def get_current_tenant_id():
    return _current_tenant_id.get()


def get_subdomain_from_host(host: str | None) -> str | None:
    if not host:
        return None
    normalized_host = host.split(":")[0].strip().lower()
    parts = normalized_host.split(".")
    if len(parts) < 3:
        return None
    subdomain = parts[0]
    if subdomain in RESERVED_SUBDOMAINS:
        return None
    return subdomain


def get_subdomain_from_request(request: HttpRequest) -> str | None:
    return get_subdomain_from_host(request.get_host())
