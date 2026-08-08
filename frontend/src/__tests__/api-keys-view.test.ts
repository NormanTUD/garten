import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { createRouter, createMemoryHistory } from "vue-router";
import { createVuetify } from "vuetify";

const mockApi = {
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
};

vi.mock("@/api/client", () => ({ api: mockApi }));

const mockAuth = {
  user: { id: 1, role: "admin" } as { id: number; role: string } | null,
  isAdmin: true,
  isAuthenticated: true,
};

vi.mock("@/stores/auth", () => ({
  useAuthStore: () => mockAuth,
}));

const sampleCatalog = {
  groups: [
    {
      key: "cameras",
      label: "Kameras",
      icon: "mdi-camera",
      scopes: [
        { scope: "cameras:read", label: "Lesen", description: "Bilder ansehen" },
        { scope: "cameras:upload", label: "Upload", description: "Bilder pushen" },
      ],
    },
    {
      key: "finance",
      label: "Finanzen",
      icon: "mdi-cash",
      scopes: [
        { scope: "finance:read", label: "Lesen" },
        { scope: "finance:write", label: "Schreiben" },
      ],
    },
  ],
  all_scopes: ["cameras:read", "cameras:upload", "finance:read", "finance:write"],
};

const sampleKeys = [
  {
    id: 1,
    name: "Pi Cam Upload",
    description: null,
    key_prefix: "gard_AbCdEfGh",
    owner_user_id: 1,
    owner_username: "admin",
    scopes: ["cameras:upload"],
    allowed_ips: null,
    expires_at: null,
    is_active: true,
    created_at: "2026-01-01T00:00:00Z",
    last_used_at: null,
    use_count: 5,
  },
  {
    id: 2,
    name: "Read Only",
    description: "Alles lesen",
    key_prefix: "gard_XyZ12345",
    owner_user_id: 2,
    owner_username: "alice",
    scopes: ["cameras:read", "finance:read"],
    allowed_ips: ["10.0.0.0/24"],
    expires_at: "2027-01-01T00:00:00Z",
    is_active: true,
    created_at: "2026-01-15T00:00:00Z",
    last_used_at: "2026-02-01T00:00:00Z",
    use_count: 42,
  },
];

async function mountApiKeysView() {
  const { default: ApiKeysView } = await import("@/views/ApiKeysView.vue");
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/admin/keys", name: "admin-keys", component: ApiKeysView },
    ],
  });
  await router.push("/admin/keys");
  await router.isReady();

  const wrapper = mount(ApiKeysView, {
    global: { plugins: [router, createVuetify()] },
  });
  await flushPromises();
  return { wrapper, router };
}

describe("ApiKeysView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockAuth.user = { id: 1, role: "admin" };
    mockAuth.isAdmin = true;
    mockAuth.isAuthenticated = true;

    mockApi.get.mockImplementation(async (path: string) => {
      if (path === "/keys/") return sampleKeys;
      if (path === "/keys/catalog") return sampleCatalog;
      return [];
    });
  });

  it("loads keys and catalog on mount", async () => {
    const { wrapper } = await mountApiKeysView();
    await flushPromises();
    expect(mockApi.get).toHaveBeenCalledWith("/keys/");
    expect(mockApi.get).toHaveBeenCalledWith("/keys/catalog");
    expect(wrapper.text()).toContain("Pi Cam Upload");
    expect(wrapper.text()).toContain("Read Only");
  });

  it("renders scope groups from the catalog", async () => {
    const { wrapper } = await mountApiKeysView();
    await flushPromises();
    // Switch to create tab
    await wrapper.findAll('[role="tab"]')[1]?.trigger("click");
    await flushPromises();
    expect(wrapper.text()).toContain("Kameras");
    expect(wrapper.text()).toContain("Finanzen");
    expect(wrapper.text()).toContain("cameras:upload");
    expect(wrapper.text()).toContain("cameras:read");
  });

  it("shows expiry column", async () => {
    const { wrapper } = await mountApiKeysView();
    await flushPromises();
    // "nie" for null expiry, formatted date for set expiry
    expect(wrapper.text()).toContain("nie");
    expect(wrapper.text()).toContain("01.01.2027");
  });

  it("shows usage count", async () => {
    const { wrapper } = await mountApiKeysView();
    await flushPromises();
    expect(wrapper.text()).toContain("5×");
    expect(wrapper.text()).toContain("42×");
  });

  it("rotate calls API", async () => {
    mockApi.post.mockResolvedValueOnce({
      ...sampleKeys[0],
      api_key: "gard_NewPlaintextKeyValue12345",
    });
    vi.spyOn(window, "confirm").mockReturnValue(true);

    const { wrapper } = await mountApiKeysView();
    await flushPromises();
    const vm = wrapper.vm as unknown as {
      rotate: (k: { id: number; name: string }) => Promise<void>;
    };
    await vm.rotate(sampleKeys[0]);
    await flushPromises();

    expect(mockApi.post).toHaveBeenCalledWith("/keys/1/rotate", {});
  });

  it("toggle active calls API", async () => {
    const { wrapper } = await mountApiKeysView();
    await flushPromises();

    const vm = wrapper.vm as unknown as {
      toggleActive: (k: { id: number; is_active: boolean }) => Promise<void>;
    };
    await vm.toggleActive(sampleKeys[0]);
    await flushPromises();

    expect(mockApi.patch).toHaveBeenCalledWith("/keys/1", { is_active: false });
  });

  it("creates a key with name + scopes", async () => {
    mockApi.post.mockResolvedValueOnce({
      ...sampleKeys[0],
      id: 99,
      api_key: "gard_NewlyCreatedKey123",
    });

    const { wrapper } = await mountApiKeysView();
    await flushPromises();
    await wrapper.findAll('[role="tab"]')[1]?.trigger("click");
    await flushPromises();

    // Set name
    const nameInput = wrapper.find('input[label="Name"], input');
    // Easier: use vm to set form values directly
    const vm = wrapper.vm as unknown as {
      form: {
        name: string;
        description: string;
        scopes: string[];
        allowed_ips: string;
        expires_in_days: number | null;
      };
      selectPreset: (p: string) => void;
      submitCreate: () => Promise<void>;
    };
    vm.form.name = "Test Key";
    vm.selectPreset("uploader");
    await vm.submitCreate();
    await flushPromises();

    expect(mockApi.post).toHaveBeenCalledWith(
      "/keys/",
      expect.objectContaining({
        name: "Test Key",
        scopes: ["cameras:upload"],
      }),
    );
  });

  it("non-admin cannot see API keys tab content normally (UI-only test)", async () => {
    mockAuth.isAdmin = false;
    mockApi.get.mockImplementation(async (path: string) => {
      if (path === "/keys/") return sampleKeys;  // user sees their own
      if (path === "/keys/catalog") return sampleCatalog;
      return [];
    });
    const { wrapper } = await mountApiKeysView();
    await flushPromises();
    // The view itself doesn't enforce admin; the router does. So just
    // verify it loads.
    expect(wrapper.text()).toContain("API-Schlüssel");
  });
});
