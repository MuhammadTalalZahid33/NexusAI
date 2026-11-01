/**
 * Central API client for talking to the Nexus AI backend.
 *
 * Everything that calls the backend goes through this module. Keeping it in
 * one place means auth headers, error handling, and the base URL are defined
 * once -- when we add login, uploads, and chat, they extend this file rather
 * than scattering fetch() calls across components.
 */

// Vite exposes env vars prefixed with VITE_ on import.meta.env.
// We fall back to the local backend if nothing is configured.
const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

/** Shape of the backend /health response (mirrors the Pydantic model). */
export interface HealthResponse {
  status: string;
  app_env: string;
  version: string;
}

/** Thrown when the backend responds but with a non-2xx status. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Low-level JSON GET helper. Centralizes URL building and error handling so
 * every endpoint behaves consistently.
 */
async function getJson<T>(path: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { Accept: "application/json" },
    });
  } catch (cause) {
    // Network-level failure (backend down, DNS, CORS preflight blocked, ...).
    throw new ApiError(0, "Could not reach the backend. Is it running?");
  }

  if (!response.ok) {
    throw new ApiError(response.status, `Request failed (${response.status}).`);
  }

  return (await response.json()) as T;
}

/** Fetch the backend liveness status. */
export function getHealth(): Promise<HealthResponse> {
  return getJson<HealthResponse>("/health");
}

export { API_BASE_URL };
