const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean | undefined | null>;
}

interface ApiError {
  status: number;
  detail: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private getAccessToken(): string | null {
    return localStorage.getItem("access_token");
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem("refresh_token");
  }

  private setTokens(access: string, refresh?: string): void {
    localStorage.setItem("access_token", access);
    if (refresh) {
      localStorage.setItem("refresh_token", refresh);
    }
  }

  clearTokens(): void {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
  }

  private buildUrl(path: string, params?: Record<string, string | number | boolean | undefined | null>): string {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);
    if (params) {
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, String(value));
        }
      });
    }
    return url.toString();
  }

  private async refreshAccessToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) return false;

      const data = await response.json();
      this.setTokens(data.access_token);
      return true;
    } catch {
      return false;
    }
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const { method = "GET", body, headers = {}, params } = options;

    const requestHeaders: Record<string, string> = {
      "Content-Type": "application/json",
      ...headers,
    };

    const token = this.getAccessToken();
    if (token) {
      requestHeaders["Authorization"] = `Bearer ${token}`;
    }

    const url = this.buildUrl(path, params);

    let response: Response;
    try {
      response = await fetch(url, {
        method,
        headers: requestHeaders,
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (networkErr) {
      // Network / CORS / proxy failure – surface a clear error instead
      // of letting the generic TypeError bubble up.
      throw {
        status: 0,
        detail:
          "Backend nicht erreichbar. Läuft der Server auf Port 8000? " +
          "(Im Dev-Modus muss der Vite-Proxy /api → localhost:8000 weiterleiten.)",
        cause: String(networkErr),
      } as ApiError;
    }

    // If 401, try to refresh token and retry once
    if (response.status === 401 && token) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        requestHeaders["Authorization"] = `Bearer ${this.getAccessToken()}`;
        response = await fetch(url, {
          method,
          headers: requestHeaders,
          body: body ? JSON.stringify(body) : undefined,
        });
      }
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    let data: unknown = null;
    try {
      data = await response.json();
    } catch {
      // empty body – fall through
    }

    if (!response.ok) {
      const detail =
        (data && typeof data === "object" && "detail" in data
          ? (data as { detail: unknown }).detail
          : null) || `HTTP ${response.status}`;
      const error: ApiError = {
        status: response.status,
        detail: typeof detail === "string" ? detail : JSON.stringify(detail),
      };
      throw error;
    }

    return data as T;
  }

  // Convenience methods
  get<T>(path: string, params?: Record<string, string | number | boolean | undefined | null>): Promise<T> {
    return this.request<T>(path, { params });
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "POST", body });
  }

  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "PATCH", body });
  }

  put<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "PUT", body });
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>(path, { method: "DELETE" });
  }

  // Auth-specific methods
  async login(username: string, password: string): Promise<void> {
    const data = await this.post<{ access_token: string; refresh_token: string }>(
      "/auth/login",
      { username, password }
    );
    this.setTokens(data.access_token, data.refresh_token);
  }

  logout(): void {
    this.clearTokens();
  }
}

export const api = new ApiClient(API_BASE);
export type { ApiError };

