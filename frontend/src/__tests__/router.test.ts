import { describe, it, expect, beforeEach, vi } from "vitest";

// Mock the auth store with mutable state
const authState = {
  user: null as { id: number; role: string } | null,
  isAuthenticated: false,
  isAdmin: false,
  initialize: vi.fn(),
};

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => authState,
}));

async function buildFreshRouter() {
  // Re-import the router module fresh for each test
  vi.resetModules();
  // Re-mock the store after resetModules
  vi.doMock("@/stores/auth", () => ({
    useAuthStore: () => authState,
  }));
  const mod = await import("@/router");
  return mod.default;
}

describe("Router navigation guards", () => {
  beforeEach(() => {
    localStorage.clear();
    authState.user = null;
    authState.isAuthenticated = false;
    authState.isAdmin = false;
    authState.initialize.mockReset();
    authState.initialize.mockResolvedValue(undefined);
  });

  it("redirects to login when accessing protected route without auth", async () => {
    authState.isAuthenticated = false;
    localStorage.removeItem("access_token");

    const router = await buildFreshRouter();
    await router.push("/finance");
    expect(router.currentRoute.value.name).toBe("login");
  });

  it("redirects to dashboard when accessing login while authenticated", async () => {
    authState.user = { id: 1, role: "user" };
    authState.isAuthenticated = true;

    const router = await buildFreshRouter();
    await router.push("/login");
    expect(router.currentRoute.value.name).toBe("dashboard");
  });

  it("blocks non-admin from /admin route", async () => {
    authState.user = { id: 2, role: "user" };
    authState.isAuthenticated = true;
    authState.isAdmin = false;

    const router = await buildFreshRouter();
    await router.push("/admin");
    expect(router.currentRoute.value.name).toBe("dashboard");
  });

  it("allows admin to /admin route", async () => {
    authState.user = { id: 1, role: "admin" };
    authState.isAuthenticated = true;
    authState.isAdmin = true;

    const router = await buildFreshRouter();
    await router.push("/admin");
    expect(router.currentRoute.value.name).toBe("admin");
  });

  it("allows authenticated user to protected routes", async () => {
    authState.user = { id: 2, role: "user" };
    authState.isAuthenticated = true;
    authState.isAdmin = false;

    const router = await buildFreshRouter();
    await router.push("/finance");
    expect(router.currentRoute.value.name).toBe("finance");
  });

  it("calls initialize when token present but auth state empty", async () => {
    localStorage.setItem("access_token", "fake");
    authState.isAuthenticated = false;

    const router = await buildFreshRouter();
    await router.push("/finance");
    expect(authState.initialize).toHaveBeenCalled();
    // Without a user, redirects to login
    expect(router.currentRoute.value.name).toBe("login");
  });
});
