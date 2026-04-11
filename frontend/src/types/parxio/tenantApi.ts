import { HttpMethod, Type } from "@/Utils/request/types";
import {
  MonthlyIncentiveSummary,
  TenantContextRead,
} from "@/types/parxio/tenant";

export default {
  current: {
    path: "/api/v1/parxio/tenant/current/",
    method: HttpMethod.GET,
    TRes: Type<TenantContextRead>(),
  },
  incentives: {
    path: "/api/v1/parxio/facility/{facilityId}/incentives/",
    method: HttpMethod.GET,
    TRes: Type<MonthlyIncentiveSummary>(),
  },
} as const;
