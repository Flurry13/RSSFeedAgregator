const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8081";

export interface Pagination {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface ListResponse<T> {
  data: T[];
  pagination: Pagination;
}

export interface Headline {
  id: number;
  title: string;
  description?: string;
  url: string;
  source_name: string;
  topic?: string;
  language?: string;
  published_at?: string;
  created_at: string;
}

export interface Event {
  id: number;
  label: string;
  event_type?: string;
  headline_count: number;
  created_at: string;
  headlines?: Headline[];
  members?: Headline[];
}

export interface AnalyticsData {
  period: string;
  topic_distribution: { topic: string; count: number }[];
  language_breakdown: { language: string; count: number }[];
  category_breakdown: { category: string; count: number }[];
  daily_volume: { date: string; count: number }[];
  source_breakdown: { source_id: number; name: string; count: number }[];
}

export interface Source {
  id: number;
  name: string;
  url: string;
  language?: string;
  country?: string;
  category?: string;
  active: boolean;
  fetch_error?: string | null;
  error_count?: number;
  last_fetched_at?: string | null;
  created_at: string;
}

export interface PipelineStatus {
  stage: string;
  status: string;
  progress: number;
  total: number;
  message: string;
  last_run?: string;
  last_duration_ms?: number;
}

export interface SearchResult {
  id: number;
  title: string;
  description?: string;
  url: string;
  source_name: string;
  score: number;
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const url = `${BASE_URL}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

function buildQuery(params: Record<string, string | number | undefined>): string {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join("&");
  return qs ? `?${qs}` : "";
}

export const api = {
  headlines: {
    list(params: {
      page?: number;
      limit?: number;
      topic?: string;
      language?: string;
      q?: string;
    } = {}): Promise<ListResponse<Headline>> {
      return request(`/api/headlines${buildQuery(params)}`);
    },
  },

  events: {
    list(params: { page?: number; limit?: number } = {}): Promise<ListResponse<Event>> {
      return request(`/api/events${buildQuery(params)}`);
    },
    get(id: number): Promise<Event> {
      return request(`/api/events/${id}`);
    },
  },

  analytics: {
    get(period: "24h" | "7d" | "30d" = "24h"): Promise<AnalyticsData> {
      return request(`/api/analytics${buildQuery({ period })}`);
    },
  },

  sources: {
    list(params: { page?: number; limit?: number } = {}): Promise<ListResponse<Source>> {
      return request(`/api/sources${buildQuery(params)}`);
    },
    get(id: number): Promise<Source> {
      return request(`/api/sources/${id}`);
    },
    create(data: Partial<Source>): Promise<Source> {
      return request("/api/sources", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    update(id: number, data: Partial<Source>): Promise<Source> {
      return request(`/api/sources/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    delete(id: number): Promise<void> {
      return request(`/api/sources/${id}`, { method: "DELETE" });
    },
  },

  pipeline: {
    status(): Promise<PipelineStatus> {
      return request("/api/pipeline/status");
    },
    gather(): Promise<{ ok: boolean }> {
      return request("/api/gather", { method: "POST" });
    },
    translate(): Promise<{ ok: boolean }> {
      return request("/api/translate", { method: "POST" });
    },
    classify(): Promise<{ ok: boolean }> {
      return request("/api/classify", { method: "POST" });
    },
    run(): Promise<{ ok: boolean }> {
      return request("/api/run", { method: "POST" });
    },
  },

  search: {
    query(q: string, limit = 10): Promise<SearchResult[]> {
      return request(`/api/search${buildQuery({ q, limit })}`);
    },
  },
};
