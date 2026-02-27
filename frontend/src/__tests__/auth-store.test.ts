import { describe, it, expect, beforeEach, vi } from "vitest";
import { setActivePinia, createPinia } from "pinia";
import { useAuthStore } from "@/stores/auth";

// Mock the API client
vi.mock("@/api/client", () => {
  const mockApi = {
    login: vi.fn(),
    logout: vi.fn(),
    clearTokens: vi.fn(),
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  };
  return { api: mockApi };
});

import { api } from "@/api/client";
const mockApi = vi.mocked(api);

describe("Auth Store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    localStorage.clear();
  });

  // ─── Initial State ──────────────────────────────────────────

  it("starts with no user", () => {
    const store = useAuthStore();
    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(store.isAdmin).toBe(false);
    expect(store.displayName).toBe("");
  });

  // ─── Login ──────────────────────────────────────────────────

  it("login success sets user", async () => {
    const store = useAuthStore();

    mockApi.login.mockResolvedValue(undefined);
    mockApi.get.mockResolvedValue({
      id: 1,
      username: "admin",
      display_name: "Admin User",
      role: "admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    });

    const result = await store.login("admin", "admin123");

    expect(result).toBe(true);
    expect(mockApi.login).toHaveBeenCalledWith("admin", "admin123");
    expect(mockApi.get).toHaveBeenCalledWith("/auth/me");
    expect(store.user).not.toBeNull();
    expect(store.user!.username).toBe("admin");
    expect(store.isAuthenticated).toBe(true);
    expect(store.isAdmin).toBe(true);
    expect(store.displayName).toBe("Admin User");
    expect(store.error).toBeNull();
  });

  it("login failure sets error", async () => {
    const store = useAuthStore();

    mockApi.login.mockRejectedValue({
      status: 401,
      detail: "Ungültige Anmeldedaten",
    });

    const result = await store.login("admin", "wrong");

    expect(result).toBe(false);
    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(store.error).toBe("Ungültige Anmeldedaten");
  });

  it("loading is true during login", async () => {
    const store = useAuthStore();

    let resolveLogin: () => void;
    mockApi.login.mockReturnValue(
      new Promise<void>((resolve) => {
        resolveLogin = resolve;
      })
    );
    mockApi.get.mockResolvedValue({
      id: 1,
      username: "admin",
      display_name: "Admin",
      role: "admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    });

    const loginPromise = store.login("admin", "admin123");
    expect(store.loading).toBe(true);

    resolveLogin!();
    await loginPromise;
    expect(store.loading).toBe(false);
  });

  // ─── Logout ─────────────────────────────────────────────────

  it("logout clears user", async () => {
    const store = useAuthStore();

    // Set up logged-in state
    mockApi.login.mockResolvedValue(undefined);
    mockApi.get.mockResolvedValue({
      id: 1,
      username: "admin",
      display_name: "Admin",
      role: "admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    });
    await store.login("admin", "admin123");
    expect(store.isAuthenticated).toBe(true);

    await store.logout();

    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(mockApi.logout).toHaveBeenCalled();
  });

  // ─── Role Detection ─────────────────────────────────────────

  it("detects normal user role", async () => {
    const store = useAuthStore();

    mockApi.login.mockResolvedValue(undefined);
    mockApi.get.mockResolvedValue({
      id: 2,
      username: "user1",
      display_name: "Normal User",
      role: "user",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    });

    await store.login("user1", "pass");

    expect(store.isAdmin).toBe(false);
    expect(store.isAuthenticated).toBe(true);
    expect(store.displayName).toBe("Normal User");
  });

  // ─── Initialize ─────────────────────────────────────────────

  it("initialize fetches user when token exists", async () => {
    const store = useAuthStore();
    localStorage.setItem("access_token", "fake-token");

    mockApi.get.mockResolvedValue({
      id: 1,
      username: "admin",
      display_name: "Admin",
      role: "admin",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    });

    await store.initialize();

    expect(store.isAuthenticated).toBe(true);
    expect(mockApi.get).toHaveBeenCalledWith("/auth/me");
  });

  it("initialize does nothing without token", async () => {
    const store = useAuthStore();

    await store.initialize();

    expect(store.isAuthenticated).toBe(false);
    expect(mockApi.get).not.toHaveBeenCalled();
  });

  it("initialize clears state on failed fetch", async () => {
    const store = useAuthStore();
    localStorage.setItem("access_token", "expired-token");

    mockApi.get.mockRejectedValue({ status: 401, detail: "Expired" });

    await store.initialize();

    expect(store.user).toBeNull();
    expect(store.isAuthenticated).toBe(false);
    expect(mockApi.clearTokens).toHaveBeenCalled();
  });

  // ─── Change Password ───────────────────────────────────────

  it("changePassword calls API", async () => {
    const store = useAuthStore();
    mockApi.put.mockResolvedValue(undefined);

    await store.changePassword("old123", "new456");

    expect(mockApi.put).toHaveBeenCalledWith("/auth/me/password", {
      current_password: "old123",
      new_password: "new456",
    });
  });
});

