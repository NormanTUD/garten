<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface Device {
  id: number;
  name: string;
  device_type: string;
  hardware_id: string | null;
  location: string | null;
  is_active: boolean;
  last_seen_at: string | null;
  registered_at: string;
}

interface Valve {
  id: number;
  name: string;
  current_state: string;
  desired_state: string;
  device_id: number | null;
  is_active: boolean;
  last_change: string | null;
}

interface Camera {
  id: number;
  name: string;
  location: string | null;
  detect_faces: boolean;
  retention_days: number;
  is_active: boolean;
}

interface TimelineEvent {
  id: string;
  event_type: string;
  occurred_at: string;
  title: string;
  summary: string;
  actor_name: string | null;
  icon: string | null;
  color: string | null;
}

const tab = ref<"devices" | "cameras" | "valves" | "network" | "timeline">("devices");

const devices = ref<Device[]>([]);
const valves = ref<Valve[]>([]);
const cameras = ref<Camera[]>([]);
const timeline = ref<TimelineEvent[]>([]);
const loading = ref(false);

const showDeviceDialog = ref(false);
const newDevice = ref({ name: "", device_type: "camera", location: "" });
const newApiKey = ref<string | null>(null);

async function loadDevices() {
  loading.value = true;
  try {
    devices.value = await api.get<Device[]>("/devices/");
  } finally {
    loading.value = false;
  }
}

async function loadCameras() {
  cameras.value = await api.get<Camera[]>("/cameras/");
}

async function loadValves() {
  valves.value = await api.get<Valve[]>("/valves/");
}

async function loadTimeline() {
  const r = await api.get<{ events: TimelineEvent[] }>("/timeline/", { limit: 50 });
  timeline.value = r.events;
}

async function createDevice() {
  const result = await api.post<Device & { api_key: string }>("/devices/", newDevice.value);
  newApiKey.value = result.api_key;
  showDeviceDialog.value = false;
  newDevice.value = { name: "", device_type: "camera", location: "" };
  await loadDevices();
}

async function toggleDevice(d: Device) {
  await api.patch(`/devices/${d.id}`, { is_active: !d.is_active });
  await loadDevices();
}

async function commandValve(v: Valve, state: "open" | "closed") {
  await api.post(`/valves/${v.id}/command`, { new_state: state });
  await loadValves();
}

const filteredTimeline = computed(() => timeline.value);

function eventColor(t: string): string {
  if (t.includes("alert")) return "error";
  if (t.includes("expense")) return "red";
  if (t.includes("payment") || t.includes("harvest")) return "success";
  if (t.includes("valve_opened") || t.includes("watering")) return "info";
  return "grey";
}

onMounted(async () => {
  await Promise.all([loadDevices(), loadCameras(), loadValves(), loadTimeline()]);
});
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">IoT &amp; Gartensteuerung</h1>

    <v-tabs v-model="tab" color="primary" class="mb-4">
      <v-tab value="devices">
        <v-icon start>mdi-chip</v-icon>
        Geräte ({{ devices.length }})
      </v-tab>
      <v-tab value="cameras">
        <v-icon start>mdi-camera</v-icon>
        Kameras ({{ cameras.length }})
      </v-tab>
      <v-tab value="valves">
        <v-icon start>mdi-water-pump</v-icon>
        Ventile ({{ valves.length }})
      </v-tab>
      <v-tab value="network">
        <v-icon start>mdi-router-network</v-icon>
        MAC-Allowlist
      </v-tab>
      <v-tab value="timeline">
        <v-icon start>mdi-timeline</v-icon>
        Timeline
      </v-tab>
    </v-tabs>

    <!-- ── Devices ─────────────────────────────────────────────── -->
    <v-window v-model="tab">
      <v-window-item value="devices">
        <v-card>
          <v-card-title>
            <span>Geräte</span>
            <v-spacer />
            <v-btn
              v-if="auth.isAdmin"
              color="primary"
              prepend-icon="mdi-plus"
              @click="showDeviceDialog = true"
            >
              Gerät registrieren
            </v-btn>
          </v-card-title>
          <v-skeleton-loader v-if="loading" type="table" />
          <v-table v-else>
            <thead>
              <tr>
                <th>Name</th>
                <th>Typ</th>
                <th>Hardware-ID</th>
                <th>Ort</th>
                <th>Letzter Heartbeat</th>
                <th>Status</th>
                <th class="text-right">Aktion</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="d in devices" :key="d.id">
                <td>{{ d.name }}</td>
                <td><v-chip size="small">{{ d.device_type }}</v-chip></td>
                <td>{{ d.hardware_id || "—" }}</td>
                <td>{{ d.location || "—" }}</td>
                <td>
                  {{ d.last_seen_at ? new Date(d.last_seen_at).toLocaleString("de-DE") : "nie" }}
                </td>
                <td>
                  <v-chip
                    :color="d.is_active ? 'success' : 'grey'"
                    size="small"
                    variant="flat"
                  >
                    {{ d.is_active ? "aktiv" : "inaktiv" }}
                  </v-chip>
                </td>
                <td class="text-right">
                  <v-btn
                    size="small"
                    :icon="d.is_active ? 'mdi-power' : 'mdi-power-standby'"
                    :color="d.is_active ? 'error' : 'success'"
                    variant="text"
                    @click="toggleDevice(d)"
                  />
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-window-item>

      <!-- ── Cameras ────────────────────────────────────────────── -->
      <v-window-item value="cameras">
        <v-card>
          <v-card-title>Kameras</v-card-title>
          <v-table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Ort</th>
                <th>Retention</th>
                <th>Gesichtserkennung</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in cameras" :key="c.id">
                <td>{{ c.name }}</td>
                <td>{{ c.location || "—" }}</td>
                <td>{{ c.retention_days }} Tage</td>
                <td>
                  <v-icon :color="c.detect_faces ? 'success' : 'grey'">
                    {{ c.detect_faces ? "mdi-check" : "mdi-close" }}
                  </v-icon>
                </td>
                <td>
                  <v-chip :color="c.is_active ? 'success' : 'grey'" size="small">
                    {{ c.is_active ? "aktiv" : "inaktiv" }}
                  </v-chip>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-window-item>

      <!-- ── Valves ─────────────────────────────────────────────── -->
      <v-window-item value="valves">
        <v-card>
          <v-card-title>Ventile</v-card-title>
          <v-table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Soll-Zustand</th>
                <th>Ist-Zustand</th>
                <th>Status</th>
                <th class="text-right">Manuell</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="v in valves" :key="v.id">
                <td>{{ v.name }}</td>
                <td>
                  <v-chip
                    :color="v.desired_state === 'open' ? 'blue' : 'grey'"
                    size="small"
                  >
                    {{ v.desired_state }}
                  </v-chip>
                </td>
                <td>
                  <v-chip
                    :color="v.current_state === 'open' ? 'blue' : 'grey'"
                    size="small"
                    variant="outlined"
                  >
                    {{ v.current_state }}
                  </v-chip>
                </td>
                <td>
                  <v-chip :color="v.is_active ? 'success' : 'grey'" size="small">
                    {{ v.is_active ? "aktiv" : "inaktiv" }}
                  </v-chip>
                </td>
                <td class="text-right">
                  <v-btn
                    size="small"
                    color="blue"
                    prepend-icon="mdi-water"
                    :disabled="v.desired_state === 'open'"
                    @click="commandValve(v, 'open')"
                  >
                    Auf
                  </v-btn>
                  <v-btn
                    size="small"
                    color="grey"
                    prepend-icon="mdi-water-off"
                    :disabled="v.desired_state === 'closed'"
                    class="ml-2"
                    @click="commandValve(v, 'closed')"
                  >
                    Zu
                  </v-btn>
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-window-item>

      <!-- ── Network allowlist ─────────────────────────────────── -->
      <v-window-item value="network">
        <NetworkAllowlist />
      </v-window-item>

      <!-- ── Timeline ──────────────────────────────────────────── -->
      <v-window-item value="timeline">
        <v-card>
          <v-card-title>Letzte Aktivitäten</v-card-title>
          <v-timeline density="compact" align="start">
            <v-timeline-item
              v-for="ev in filteredTimeline"
              :key="ev.id"
              :dot-color="eventColor(ev.event_type)"
              size="small"
            >
              <div class="d-flex">
                <strong class="me-2">{{ ev.title }}</strong>
                <span class="text-caption">{{
                  new Date(ev.occurred_at).toLocaleString("de-DE")
                }}</span>
              </div>
              <div>{{ ev.summary }}</div>
              <div v-if="ev.actor_name" class="text-caption text-medium-emphasis">
                von {{ ev.actor_name }}
              </div>
            </v-timeline-item>
          </v-timeline>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- ── Register device dialog ──────────────────────────────── -->
    <v-dialog v-model="showDeviceDialog" max-width="500">
      <v-card>
        <v-card-title>Neues IoT-Gerät registrieren</v-card-title>
        <v-card-text>
          <v-text-field v-model="newDevice.name" label="Name" />
          <v-select
            v-model="newDevice.device_type"
            label="Typ"
            :items="['camera', 'valve_controller', 'sensor']"
          />
          <v-text-field v-model="newDevice.location" label="Ort (optional)" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeviceDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" @click="createDevice">Registrieren</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ── Show API key once ───────────────────────────────────── -->
    <v-dialog
      :model-value="newApiKey !== null"
      max-width="600"
      persistent
      @update:model-value="(v) => { if (!v) newApiKey = null; }"
    >
      <v-card>
        <v-card-title class="text-warning">
          ⚠ API-Key – bitte sofort notieren!
        </v-card-title>
        <v-card-text>
          <p>Der API-Key wird nur <strong>einmal</strong> angezeigt.</p>
          <v-text-field :model-value="newApiKey ?? ''" readonly class="mt-3" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn color="primary" @click="newApiKey = null">Verstanden</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
