export type ComponentHealth = {
  ok: boolean;
  detail: string;
};

export type HealthResponse = {
  status: string;
  components: Record<string, ComponentHealth>;
};

export async function getHealth(): Promise<HealthResponse | null> {
  const baseUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

  try {
    const response = await fetch(`${baseUrl}/health`, { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as HealthResponse;
  } catch {
    return null;
  }
}
