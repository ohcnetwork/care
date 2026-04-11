const RESERVED_SUBDOMAINS = new Set(["app", "www", "localhost"]);

export function getTenantSubdomain(hostname = window.location.hostname) {
  const parts = hostname.split(".");
  if (parts.length < 3) return null;
  const subdomain = parts[0]?.toLowerCase();
  if (!subdomain || RESERVED_SUBDOMAINS.has(subdomain)) {
    return null;
  }
  return subdomain;
}

export function isAdminHost(hostname = window.location.hostname) {
  return getTenantSubdomain(hostname) === null;
}
