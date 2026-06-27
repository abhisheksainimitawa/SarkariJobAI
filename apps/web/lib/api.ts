const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}/api/v1${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export const api = {
  register: (body: { email: string; password: string; full_name: string }) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(body) }),

  login: (body: { email: string; password: string }) =>
    request("/auth/login", { method: "POST", body: JSON.stringify(body) }),

  logout: () => request("/auth/logout", { method: "POST" }),

  getProfile: () => request<Record<string, unknown>>("/profile"),

  updateProfile: (body: Record<string, unknown>) =>
    request("/profile", { method: "PUT", body: JSON.stringify(body) }),

  getJobs: (page = 1) =>
    request<{ jobs: Job[]; total: number; page: number; message?: string }>(`/jobs?page=${page}`),
};

export interface Job {
  id: string;
  title: string;
  organization: string;
  source_name: string;
  apply_url: string | null;
  deadline: string | null;
  published_at: string;
}
