/**
 * Typed API client for the CoachX Media AI FastAPI backend.
 * Base URL is configured via NEXT_PUBLIC_API_BASE_URL.
 *
 * Security note: Access and refresh tokens are stored in localStorage for
 * simplicity. This makes them accessible to any JavaScript running on the
 * page (XSS risk). Ensure the application has thorough XSS protections
 * (Content-Security-Policy, input sanitisation, etc.) and consider
 * migrating to httpOnly cookies for production deployments.
 */

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

// ---------------------------------------------------------------------------
// Token storage helpers (localStorage – client-only)
// ---------------------------------------------------------------------------

export const TOKEN_KEY = "access_token";
export const REFRESH_KEY = "refresh_token";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_KEY);
}

export function setTokens(access: string, refresh: string): void {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type?: string;
}

export interface UserRead {
  id: string;
  email: string;
  full_name?: string | null;
  avatar_url?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface ProjectRead {
  id: string;
  name: string;
  description?: string | null;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectCreate {
  name: string;
  description?: string;
}

export interface ProjectUpdate {
  name?: string;
  description?: string;
}

export interface MediaRead {
  id: string;
  project_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  storage_key: string;
  created_at: string;
}

export interface JobRead {
  id: string;
  project_id?: string | null;
  media_id?: string | null;
  job_type: string;
  status: string;
  result?: Record<string, unknown> | null;
  error?: string | null;
  created_at: string;
  updated_at: string;
}

export interface JobCreate {
  project_id?: string;
  media_id?: string;
  job_type: string;
  params?: Record<string, unknown>;
}

export interface SubscriptionStatus {
  status: string;
  plan?: string | null;
  current_period_end?: string | null;
}

export interface CheckoutSession {
  url: string;
}

export interface BillingPortal {
  url: string;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper with automatic token refresh
// ---------------------------------------------------------------------------

let refreshPromise: Promise<string | null> | null = null;

async function doRefresh(): Promise<string | null> {
  const rt = getRefreshToken();
  if (!rt) return null;
  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: rt }),
    });
    if (!res.ok) {
      clearTokens();
      return null;
    }
    const data: TokenResponse = await res.json();
    setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    clearTokens();
    return null;
  }
}

async function refreshOnce(): Promise<string | null> {
  if (!refreshPromise) {
    refreshPromise = doRefresh().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

type FetchOptions = Omit<RequestInit, "body"> & {
  json?: unknown;
  formData?: FormData;
  rawBody?: BodyInit;
  skipAuth?: boolean;
};

async function apiFetch<T = unknown>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { json, formData, rawBody, skipAuth, ...rest } = options;

  const headers: Record<string, string> = {};

  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  if (!skipAuth) {
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const init: RequestInit = {
    ...rest,
    headers: { ...headers, ...(rest.headers as Record<string, string>) },
    body: json !== undefined ? JSON.stringify(json) : formData ?? rawBody,
  };

  let res = await fetch(`${BASE_URL}${path}`, init);

  // Attempt token refresh on 401
  if (res.status === 401 && !skipAuth) {
    const newToken = await refreshOnce();
    if (newToken) {
      const retryHeaders = {
        ...init.headers,
        Authorization: `Bearer ${newToken}`,
      } as Record<string, string>;
      res = await fetch(`${BASE_URL}${path}`, {
        ...init,
        headers: retryHeaders,
      });
    }
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const err = await res.json();
      message = err.detail ?? JSON.stringify(err);
    } catch {
      // ignore parse error
    }
    throw new Error(message);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const auth = {
  signup(email: string, password: string, full_name?: string) {
    return apiFetch<TokenResponse>("/auth/signup", {
      method: "POST",
      json: { email, password, full_name },
      skipAuth: true,
    });
  },
  login(email: string, password: string) {
    return apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      json: { email, password },
      skipAuth: true,
    });
  },
  refresh(refresh_token: string) {
    return apiFetch<TokenResponse>("/auth/refresh", {
      method: "POST",
      json: { refresh_token },
      skipAuth: true,
    });
  },
  logout() {
    return apiFetch<void>("/auth/logout", { method: "POST" });
  },
};

// ---------------------------------------------------------------------------
// Users
// ---------------------------------------------------------------------------

export const users = {
  me() {
    return apiFetch<UserRead>("/users/me");
  },
  updateMe(data: { full_name?: string; avatar_url?: string }) {
    return apiFetch<UserRead>("/users/me", { method: "PATCH", json: data });
  },
};

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

export const projects = {
  list() {
    return apiFetch<ProjectRead[]>("/projects");
  },
  get(id: string) {
    return apiFetch<ProjectRead>(`/projects/${id}`);
  },
  create(data: ProjectCreate) {
    return apiFetch<ProjectRead>("/projects", { method: "POST", json: data });
  },
  update(id: string, data: ProjectUpdate) {
    return apiFetch<ProjectRead>(`/projects/${id}`, {
      method: "PUT",
      json: data,
    });
  },
  delete(id: string) {
    return apiFetch<void>(`/projects/${id}`, { method: "DELETE" });
  },
};

// ---------------------------------------------------------------------------
// Media
// ---------------------------------------------------------------------------

export const media = {
  listForProject(projectId: string) {
    return apiFetch<MediaRead[]>(`/projects/${projectId}/media`);
  },
  get(id: string) {
    return apiFetch<MediaRead>(`/media/${id}`);
  },
  upload(projectId: string, file: File) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("project_id", projectId);
    return apiFetch<MediaRead>("/media/upload", {
      method: "POST",
      formData: fd,
    });
  },
  delete(id: string) {
    return apiFetch<void>(`/media/${id}`, { method: "DELETE" });
  },
};

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

export const jobs = {
  list() {
    return apiFetch<JobRead[]>("/jobs");
  },
  get(id: string) {
    return apiFetch<JobRead>(`/jobs/${id}`);
  },
  create(data: JobCreate) {
    return apiFetch<JobRead>("/jobs", { method: "POST", json: data });
  },
  delete(id: string) {
    return apiFetch<void>(`/jobs/${id}`, { method: "DELETE" });
  },
  /**
   * Submit two videos and receive the rendered before/after MP4 as a Blob.
   * Phase 1 synchronous endpoint — the server processes inline, so expect
   * the request to take roughly as long as the video duration.
   */
  async comparison(before: File, after: File): Promise<Blob> {
    const fd = new FormData();
    fd.append("before", before);
    fd.append("after", after);

    const headers: Record<string, string> = {};
    const token = getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;

    const res = await fetch(`${BASE_URL}/jobs/comparison`, {
      method: "POST",
      headers,
      body: fd,
    });

    if (!res.ok) {
      let message = `HTTP ${res.status}`;
      try {
        const err = await res.json();
        message = err.detail ?? JSON.stringify(err);
      } catch {
        // not JSON
      }
      throw new Error(message);
    }
    return res.blob();
  },
};

// ---------------------------------------------------------------------------
// Payments
// ---------------------------------------------------------------------------

export const payments = {
  subscription() {
    return apiFetch<SubscriptionStatus>("/payments/subscription");
  },
  createCheckoutSession() {
    return apiFetch<CheckoutSession>("/payments/create-checkout-session", {
      method: "POST",
    });
  },
  openPortal() {
    return apiFetch<BillingPortal>("/payments/portal", { method: "POST" });
  },
};
