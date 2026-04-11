import { useQuery } from "@tanstack/react-query";
import { ReactNode, createContext, useContext } from "react";

import Loading from "@/components/Common/Loading";

import query from "@/Utils/request/query";
import tenantApi from "@/types/parxio/tenantApi";
import { TenantContextRead } from "@/types/parxio/tenant";

const TenantContext = createContext<TenantContextRead | null>(null);

export function TenantProvider({ children }: { children: ReactNode }) {
  const { data, isLoading } = useQuery({
    queryKey: ["tenant-context"],
    queryFn: query(tenantApi.current, { silent: true }),
    staleTime: 1000 * 60 * 5,
  });

  if (isLoading) {
    return <Loading />;
  }

  return (
    <TenantContext.Provider
      value={
        data ?? {
          tenant: null,
          subdomain: null,
          brand_name: "Parxio",
          logo_url: null,
          plan_tier: null,
          is_admin_host: true,
        }
      }
    >
      {children}
    </TenantContext.Provider>
  );
}

export function useTenantContext() {
  const ctx = useContext(TenantContext);
  if (!ctx) {
    throw new Error("'useTenantContext' must be used within TenantProvider");
  }
  return ctx;
}
