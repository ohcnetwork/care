export interface TenantContextRead {
  tenant: string | null;
  subdomain: string | null;
  brand_name: string;
  logo_url: string | null;
  plan_tier: "Lite" | "Pro" | null;
  is_admin_host: boolean;
}

export interface MonthlyIncentiveSummary {
  doctor_total: string;
  parxio_total: string;
  patient_count: number;
  threshold_target: number;
  threshold_progress: number;
}
