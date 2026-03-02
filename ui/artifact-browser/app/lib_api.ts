export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") || "http://localhost:8000";

export const DEFAULT_AUTH_TOKEN =
  process.env.NEXT_PUBLIC_AUTH_TOKEN || "";

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const url = `${API_BASE}${path}`;
  const token = DEFAULT_AUTH_TOKEN;

  return fetch(url, {
    ...init,
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
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

export async function postJson<T>(path: string, body: any): Promise<T> {
  const r = await apiFetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
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
  tenant_id?: string;
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
  items: Array<any>;
};
