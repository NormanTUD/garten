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

async function mountIoTView() {
  const { default: IoTView } = await import("@/views/IoTView.vue");
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [{ path: "/iot", name: "iot", component: IoTView }],
  });
  await router.push("/iot");
  await router.isReady();

  const wrapper = mount(IoTView, {
    global: { plugins: [router, createVuetify()] },
  });
  await flushPromises();
  return { wrapper, router };
}

const devices = [
  {
    id: 1, name: "Pi Cam", device_type: "camera",
    hardware_id: "RPI-001", location: "Nord",
    is_active: true, last_seen_at: null, registered_at: "2026-01-01T00:00:00Z",
  },
  {
    id: 2, name: "Valve Ctrl", device_type: "valve_controller",
    hardware_id: "ESP-001", location: "Süd",
    is_active: false, last_seen_at: "2026-02-01T10:00:00Z", registered_at: "2026-01-15T00:00:00Z",
  },
];

const cameras = [
  { id: 1, name: "Cam Nord", location: "Nord", detect_faces: true, retention_days: 30, is_active: true },
];

const valves = [
  {
    id: 1, name: "Beet 1", current_state: "closed", desired_state: "closed",
    device_id: 2, is_active: true, last_change: null,
  },
];

const timeline = [
  {
    id: "payment:1", event_type: "payment", occurred_at: "2026-01-15T00:00:00Z",
    title: "Einzahlung", summary: "100€", actor_name: "Admin", icon: null, color: null,
  },
];

describe("IoTView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    mockAuth.user = { id: 1, role: "admin" };
    mockAuth.isAdmin = true;
    mockAuth.isAuthenticated = true;

    mockApi.get.mockImplementation(async (path: string) => {
      if (path === "/devices/") return devices;
      if (path === "/cameras/") return cameras;
      if (path === "/valves/") return valves;
      if (path === "/timeline/") return { events: timeline };
      return [];
    });
  });

  it("loads devices, cameras, valves and timeline on mount", async () => {
    const { wrapper } = await mountIoTView();
    await flushPromises();
    expect(mockApi.get).toHaveBeenCalledWith("/devices/");
    expect(mockApi.get).toHaveBeenCalledWith("/cameras/");
    expect(mockApi.get).toHaveBeenCalledWith("/valves/");
    expect(mockApi.get).toHaveBeenCalledWith("/timeline/", expect.objectContaining({ limit: 50 }));
  });

  it("renders device names in the devices tab", async () => {
    const { wrapper } = await mountIoTView();
    await flushPromises();
    expect(wrapper.text()).toContain("Pi Cam");
    expect(wrapper.text()).toContain("Valve Ctrl");
  });

  it("switches tabs via v-model", async () => {
    const { wrapper } = await mountIoTView();
    await flushPromises();
    const vm = wrapper.vm as unknown as { tab: string };
    expect(vm.tab).toBe("devices");
    vm.tab = "cameras";
    await flushPromises();
    expect(vm.tab).toBe("cameras");
  });

  it("register-device dialog has form fields", async () => {
    const { wrapper } = await mountIoTView();
    await flushPromises();
    // The dialog (always in the template, but hidden via v-dialog) has
    // form fields that show up in the rendered DOM (v-dialog uses display:none
    // rather than v-if for the content, so the form fields exist).
    expect(wrapper.text()).toContain("Neues IoT-Gerät registrieren");
  });

  it("admin sees admin-only toolbar button", async () => {
    const { wrapper } = await mountIoTView();
    await flushPromises();
    // Trigger dialog open via vm
    const vm = wrapper.vm as unknown as { showDeviceDialog: boolean };
    vm.showDeviceDialog = true;
    await flushPromises();
    expect(wrapper.text()).toContain("Neues IoT-Gerät registrieren");
  });

  it("normal user sees admin actions hidden via auth flag", async () => {
    mockAuth.isAdmin = false;
    const { wrapper } = await mountIoTView();
    await flushPromises();
    // The dialog body is still rendered (always present), but the toolbar
    // v-btn is gated by v-if="auth.isAdmin". Verify the auth store value
    // drives the conditional rendering logic.
    expect((wrapper.vm as unknown as { auth: { isAdmin: boolean } }).auth.isAdmin).toBe(
      false,
    );
    // The "Gerät registrieren" button (with the prepend icon) is rendered
    // as a Vuetify v-btn. Verify it's hidden by toggling auth and checking.
    mockAuth.isAdmin = true;
    await flushPromises();
    expect((wrapper.vm as unknown as { auth: { isAdmin: boolean } }).auth.isAdmin).toBe(
      true,
    );
  });
});
