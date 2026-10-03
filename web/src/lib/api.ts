export type ComponentHealth = {
  ok: boolean;
  detail: string;
};

export type HealthResponse = {
  status: string;
  components: Record<string, ComponentHealth>;
};

export type HwpxFormJobSummary = {
  job_id: string;
  created_at: string;
  source_filename: string;
  original_filename: string;
  output_filename: string;
  download_url: string;
  filled_count: number;
  missing_count: number;
  skipped_count: number;
  trim_applied: boolean;
};

export type HwpxFormJobDetail = HwpxFormJobSummary & {
  filled: string[];
  missing: Array<Record<string, string>>;
  skipped: Array<Record<string, string>>;
  mappings: Array<Record<string, unknown>>;
};

export type CompanyDataSnapshot = {
  company: Record<string, unknown>;
  personnel: Array<Record<string, unknown>>;
  personnel_careers: Array<Record<string, unknown>>;
  track_records: Array<Record<string, unknown>>;
};

export const apiBaseUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
export const publicApiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse | null> {
  try {
    const response = await fetch(`${apiBaseUrl}/health`, { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}

export async function getHwpxFormJobs(limit = 50): Promise<HwpxFormJobSummary[]> {
  const response = await fetch(`${apiBaseUrl}/forms/hwpx/jobs?limit=${limit}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as HwpxFormJobSummary[];
}

export async function getHwpxFormJob(jobId: string): Promise<HwpxFormJobDetail | null> {
  const response = await fetch(`${apiBaseUrl}/forms/hwpx/jobs/${jobId}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as HwpxFormJobDetail;
}

export async function getCompanyDataSnapshot(): Promise<CompanyDataSnapshot> {
  const response = await fetch(`${apiBaseUrl}/integrations/company/snapshot`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return {
      company: {},
      personnel: [],
      personnel_careers: [],
      track_records: [],
    };
  }
  return (await response.json()) as CompanyDataSnapshot;
}
