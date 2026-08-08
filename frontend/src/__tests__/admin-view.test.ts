import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import { createVuetify } from "vuetify";

const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
};

vi.mock("@/api/client", () => ({ api: mockApi }));

const mockAuth = {
  user: { id: 1, username: "admin", role: "admin", display_name: "Admin" } as {
    id: number;
    username: string;
    role: string;
    display_name: string;
  } | null,
  isAdmin: true,
};

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => mockAuth,
}));

async function mountAdminView() {
  const { default: AdminView } = await import("@/views/AdminView.vue");
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "dashboard", component: { template: "<div />" } },
      { path: "/admin", name: "admin", component: AdminView },
    ],
  });
  await router.push("/admin");
  await router.isReady();

  const wrapper = mount(AdminView, {
    global: {
      plugins: [router, createVuetify()],
    },
  });
  await flushPromises();
  return { wrapper, router };
}

const sampleUsers = [
  {
    id: 1,
    username: "admin",
    display_name: "Administrator",
    role: "admin",
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2,
    username: "alice",
    display_name: "Alice",
    role: "user",
    is_active: true,
    created_at: "2026-01-15T00:00:00Z",
  },
  {
    id: 3,
    username: "bob",
    display_name: "Bob",
    role: "user",
    is_active: false,
    created_at: "2026-02-01T00:00:00Z",
  },
];

describe("AdminView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockAuth.user = { id: 1, username: "admin", role: "admin", display_name: "Admin" };
    mockAuth.isAdmin = true;
  });

  it("loads users on mount and renders them", async () => {
    mockApi.get.mockResolvedValueOnce(sampleUsers);

    const { wrapper } = await mountAdminView();
    await flushPromises();

    expect(mockApi.get).toHaveBeenCalledWith("/users/");
    const text = wrapper.text();
    expect(text).toContain("Administrator");
    expect(text).toContain("Alice");
    expect(text).toContain("Bob");
  });

  it("shows deactivated indicator for inactive users", async () => {
    mockApi.get.mockResolvedValueOnce(sampleUsers);

    const { wrapper } = await mountAdminView();
    await flushPromises();
    expect(wrapper.text()).toContain("Deaktiviert");
  });

  it("rejects short passwords client-side", async () => {
    mockApi.get.mockResolvedValueOnce([]);
    const { wrapper } = await mountAdminView();
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      openCreateDialog: () => void;
      createUser: () => Promise<void>;
      createForm: { username: string; password: string; display_name: string; role: string };
      createError: string;
    };

    vm.openCreateDialog();
    vm.createForm.username = "carol";
    vm.createForm.display_name = "Carol";
    vm.createForm.password = "abc";  // too short
    await vm.createUser();
    await flushPromises();

    expect(vm.createError).toContain("6 Zeichen");
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("requires all fields for create", async () => {
    mockApi.get.mockResolvedValueOnce([]);
    const { wrapper } = await mountAdminView();
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      openCreateDialog: () => void;
      createUser: () => Promise<void>;
      createForm: { username: string; password: string; display_name: string; role: string };
      createError: string;
    };

    vm.openCreateDialog();
    // Leave everything empty
    await vm.createUser();
    await flushPromises();

    expect(vm.createError).toContain("Alle Felder");
    expect(mockApi.post).not.toHaveBeenCalled();
  });

  it("creates user successfully via API", async () => {
    mockApi.get.mockResolvedValueOnce([]);
    mockApi.post.mockResolvedValueOnce({ id: 4, username: "dave" });
    mockApi.get.mockResolvedValueOnce([
      { id: 4, username: "dave", display_name: "Dave", role: "user", is_active: true, created_at: "2026-02-15T00:00:00Z" },
    ]);

    const { wrapper } = await mountAdminView();
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      openCreateDialog: () => void;
      createUser: () => Promise<void>;
      createForm: { username: string; password: string; display_name: string; role: string };
      showCreateDialog: boolean;
    };

    vm.openCreateDialog();
    vm.createForm.username = "dave";
    vm.createForm.password = "davepw123";
    vm.createForm.display_name = "Dave";
    await vm.createUser();
    await flushPromises();

    expect(mockApi.post).toHaveBeenCalledWith("/users/", expect.objectContaining({
      username: "dave",
      password: "davepw123",
      display_name: "Dave",
    }));
    expect(vm.showCreateDialog).toBe(false);
  });

  it("toggles user active state via PATCH", async () => {
    mockApi.get.mockResolvedValueOnce(sampleUsers);
    mockApi.patch.mockResolvedValueOnce({ ...sampleUsers[1], is_active: false });
    mockApi.get.mockResolvedValueOnce([
      sampleUsers[0],
      { ...sampleUsers[1], is_active: false },
      sampleUsers[2],
    ]);

    const { wrapper } = await mountAdminView();
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      toggleActive: (u: { id: number; is_active: boolean }) => Promise<void>;
    };
    await vm.toggleActive(sampleUsers[1]);
    await flushPromises();

    expect(mockApi.patch).toHaveBeenCalledWith("/users/2", { is_active: false });
  });

  it("disables deactivate button for current user", async () => {
    mockApi.get.mockResolvedValueOnce(sampleUsers);
    const { wrapper } = await mountAdminView();
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      canDeactivate: (u: { id: number; role: string }) => boolean;
    };
    expect(vm.canDeactivate(sampleUsers[0])).toBe(false); // self = admin
    expect(vm.canDeactivate(sampleUsers[1])).toBe(true);  // normal user
  });

  it("disables deactivate button for any admin", async () => {
    mockApi.get.mockResolvedValueOnce([
      sampleUsers[0],
      { ...sampleUsers[0], id: 99 }, // another admin
    ]);
    const { wrapper } = await mountAdminView();
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      canDeactivate: (u: { id: number; role: string }) => boolean;
    };
    expect(vm.canDeactivate({ id: 99, role: "admin" })).toBe(false);
  });
});
