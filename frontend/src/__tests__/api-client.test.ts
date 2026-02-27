import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

// We need to import after mocking fetch
const { api } = await import("@/api/client");

describe("API Client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    api.clearTokens();
  });

  // ─── Basic Requests ─────────────────────────────────────────

  it("GET request works", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ status: "ok" }),
    });

    const result = await api.get("/health");

    expect(result).toEqual({ status: "ok" });
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toContain("/api/health");
    expect(options.method).toBe("GET");
  });

  it("POST request sends body", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 201,
      json: () => Promise.resolve({ id: 1, name: "Test" }),
    });

    const result = await api.post("/gardens/", { name: "Test" });

    expect(result).toEqual({ id: 1, name: "Test" });
    const [, options] = mockFetch.mock.calls[0];
    expect(options.method).toBe("POST");
    expect(JSON.parse(options.body)).toEqual({ name: "Test" });
  });

  it("DELETE returns undefined for 204", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 204,
    });

    const result = await api.delete("/gardens/1");

    expect(result).toBeUndefined();
  });

  // ─── Auth Header ────────────────────────────────────────────

  it("includes auth header when token exists", async () => {
    localStorage.setItem("access_token", "test-token");

    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/auth/me");

    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers["Authorization"]).toBe("Bearer test-token");
  });

  it("no auth header without token", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({}),
    });

    await api.get("/health");

    const [, options] = mockFetch.mock.calls[0];
    expect(options.headers["Authorization"]).toBeUndefined();
  });

  // ─── Error Handling ─────────────────────────────────────────

  it("throws ApiError on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: "Not found" }),
    });

    await expect(api.get("/gardens/9999")).rejects.toEqual({
      status: 404,
      detail: "Not found",
    });
  });

  it("throws ApiError with default message", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      json: () => Promise.resolve({}),
    });

    await expect(api.get("/broken")).rejects.toEqual({
      status: 500,
      detail: "Ein Fehler ist aufgetreten",
    });
  });

  // ─── Token Refresh ──────────────────────────────────────────

  it("refreshes token on 401 and retries", async () => {
    localStorage.setItem("access_token", "expired-token");
    localStorage.setItem("refresh_token", "valid-refresh");

    // First call: 401
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Token expired" }),
    });

    // Refresh call: success
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ access_token: "new-token" }),
    });

    // Retry call: success
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ id: 1, username: "admin" }),
    });

    const result = await api.get("/auth/me");

    expect(result).toEqual({ id: 1, username: "admin" });
    expect(mockFetch).toHaveBeenCalledTimes(3);
    expect(localStorage.getItem("access_token")).toBe("new-token");
  });

  it("fails if refresh also fails", async () => {
    localStorage.setItem("access_token", "expired-token");
    localStorage.setItem("refresh_token", "also-expired");

    // First call: 401
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Token expired" }),
    });

    // Refresh call: also fails
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: "Refresh expired" }),
    });

    await expect(api.get("/auth/me")).rejects.toEqual({
      status: 401,
      detail: "Token expired",
    });
  });

  // ─── Query Params ───────────────────────────────────────────

  it("appends query params to URL", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });

    await api.get("/harvests/", { bed_id: 1, date_from: "2026-01-01" });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain("bed_id=1");
    expect(url).toContain("date_from=2026-01-01");
  });

  it("skips null and undefined params", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () => Promise.resolve([]),
    });

    await api.get("/harvests/", { bed_id: null, plant_id: undefined, user_id: 1 });

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain("bed_id");
    expect(url).not.toContain("plant_id");
    expect(url).toContain("user_id=1");
  });

  // ─── Login / Logout ─────────────────────────────────────────

  it("login stores tokens", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: () =>
        Promise.resolve({
          access_token: "access-123",
          refresh_token: "refresh-456",
        }),
    });

    await api.login("admin", "admin123");

    expect(localStorage.getItem("access_token")).toBe("access-123");
    expect(localStorage.getItem("refresh_token")).toBe("refresh-456");
  });

  it("logout clears tokens", () => {
    localStorage.setItem("access_token", "test");
    localStorage.setItem("refresh_token", "test");

    api.logout();

    expect(localStorage.getItem("access_token")).toBeNull();
    expect(localStorage.getItem("refresh_token")).toBeNull();
  });
});

