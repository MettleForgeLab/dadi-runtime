export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${API_BASE}${path}`;
  return fetch(url, {
    ...init,
    headers: {
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
}

export async function getJson<T>(path: string): Promise<T> {
  const r = await apiFetch(path);
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${path}`);
  return (await r.json()) as T;
}

export async function getBytes(path: string): Promise<Uint8Array> {
  const r = await apiFetch(path);
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${path}`);
  const buf = await r.arrayBuffer();
  return new Uint8Array(buf);
}

export function bytesToUtf8(bytes: Uint8Array): string {
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

export function tryParseJson(text: string): any | null {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

export type ArtifactMeta = {
  sha256: string;
  artifact_type: string;
  schema_version?: string | null;
  media_type: string;
  byte_length: number;
  canonical: boolean;
  canonical_format?: string | null;
  storage_backend: "postgres" | "blob";
  storage_ref?: string | null;
};

export type Edge = {
  from_sha256: string;
  to_sha256: string;
  edge_type: string;
  stage_run_id?: string | null;
  created_at?: string;
};

export type Plan = {
  plan_id: string;
  status: string;
  request: any;
  items: Array<{
    pipeline_run_id: string;
    start_stage_index: number;
    reason: string;
    affected_stage_runs: number;
    reuse_stages?: number[];
    recompute_stages?: number[];
    current_stage_outputs?: Record<string, string>;
  }>;
};
