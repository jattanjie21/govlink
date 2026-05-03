import axios, { AxiosError, type AxiosRequestConfig } from "axios";
import type { ApiErrorEnvelope, Envelope } from "./types";

/**
 * Typed error wrapping the backend's `{ error: { code, message, details } }`
 * envelope. Thrown from {@link apiGet} / {@link apiGetEnvelope} so any
 * call site (and TanStack Query) sees a consistent error shape.
 */
export class ApiError extends Error {
  /** Backend error code, e.g. `dataset_not_found`, `rate_limit_exceeded`. */
  readonly code: string;
  readonly status: number;
  readonly details?: unknown;

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.details = details;
  }

  /** True when the failure is a `404` from the backend. */
  get isNotFound() {
    return this.status === 404;
  }

  /** True when the failure is a 429 (rate limit). */
  get isRateLimited() {
    return this.status === 429;
  }
}

const baseURL = import.meta.env.VITE_API_URL ?? "/api";

export const api = axios.create({
  baseURL,
  headers: { Accept: "application/json" },
});

api.interceptors.response.use(
  (res) => res,
  (err: AxiosError<ApiErrorEnvelope | unknown>) => {
    const status = err.response?.status ?? 0;
    const payload = err.response?.data;

    if (
      payload &&
      typeof payload === "object" &&
      "error" in payload &&
      payload.error &&
      typeof payload.error === "object" &&
      "code" in payload.error &&
      "message" in payload.error
    ) {
      const e = payload.error as ApiErrorEnvelope["error"];
      return Promise.reject(new ApiError(e.code, e.message, status, e.details));
    }

    // FastAPI 422 validation errors aren't in our envelope.
    if (status === 422) {
      return Promise.reject(new ApiError("validation_error", "Invalid request parameters.", 422, payload));
    }

    return Promise.reject(
      new ApiError("network_error", err.message || "Network error", status, payload),
    );
  },
);

/**
 * GET an endpoint that returns the standard `{ data, meta }` envelope.
 * Use this when the caller needs `meta` (pagination total, snapshot_date, etc).
 */
export async function apiGetEnvelope<T>(
  path: string,
  config?: AxiosRequestConfig,
): Promise<Envelope<T>> {
  const res = await api.get<Envelope<T>>(path, config);
  return res.data;
}

/**
 * GET an endpoint and return only the `data` payload. Use for endpoints
 * where `meta` adds nothing the caller cares about.
 */
export async function apiGet<T>(
  path: string,
  config?: AxiosRequestConfig,
): Promise<T> {
  const env = await apiGetEnvelope<T>(path, config);
  return env.data;
}

/**
 * GET an endpoint that does NOT use the envelope (e.g. /admin/health, /health).
 */
export async function apiGetRaw<T>(
  path: string,
  config?: AxiosRequestConfig,
): Promise<T> {
  const res = await api.get<T>(path, config);
  return res.data;
}
