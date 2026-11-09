/**
 * Central API client for the Nexus AI backend.
 *
 * All backend calls go through here. A module-level token holder lets us attach
 * the JWT to every request after login, and a single error type keeps error
 * handling consistent across the app.
 */

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (authToken) headers.set("Authorization", `Bearer ${authToken}`);
  if (!(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers });
  } catch {
    throw new ApiError(0, "Could not reach the backend. Is it running?");
  }

  if (response.status === 204) return undefined as T;

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = (data as { detail?: string }).detail ?? `Request failed (${response.status}).`;
    throw new ApiError(response.status, detail);
  }
  return data as T;
}

// ---- Types ----
export interface HealthResponse {
  status: string;
  app_env: string;
  version: string;
}
export interface TokenResponse {
  access_token: string;
  token_type: string;
}
export interface Me {
  user_id: string;
  org_id: string;
  email: string;
  role: string;
}
export type DocumentStatus = "pending" | "processing" | "ready" | "failed";
export interface DocumentOut {
  id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  status: DocumentStatus;
  error: string | null;
  page_count: number | null;
  chunk_count: number;
  created_at: string;
}
export interface Citation {
  marker: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number | null;
  text: string;
}
export interface AskResponse {
  answer: string;
  abstained: boolean;
  citations: Citation[];
}

// ---- Endpoints ----
export const api = {
  health: () => request<HealthResponse>("/health"),

  register: (email: string, password: string, organization_name: string) =>
    request<TokenResponse>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, organization_name }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<Me>("/auth/me"),

  listDocuments: () =>
    request<{ documents: DocumentOut[] }>("/documents").then((r) => r.documents),

  getDocument: (id: string) => request<DocumentOut>(`/documents/${id}`),

  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<DocumentOut>("/documents", { method: "POST", body: form });
  },

  deleteDocument: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  ask: (question: string, opts?: { top_k?: number; strategy?: string; agentic?: boolean }) =>
    request<AskResponse>("/chat", {
      method: "POST",
      body: JSON.stringify({ question, ...opts }),
    }),
};

export { API_BASE_URL };
