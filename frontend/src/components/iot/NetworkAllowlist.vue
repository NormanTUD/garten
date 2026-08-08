<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface NetworkDevice {
  id: number;
  mac_address: string;
  name: string;
  device_type: string;
  owner_user_id: number | null;
  is_trusted: boolean;
  is_active: boolean;
  last_seen_at: string | null;
  notes: string | null;
}

const devices = ref<NetworkDevice[]>([]);
const newDevice = ref({ mac_address: "", name: "", device_type: "unknown" });
const lookupMac = ref("");
const lookupResult = ref<{
  mac_address: string;
  is_trusted: boolean;
  is_active: boolean;
  device_name: string | null;
} | null>(null);

async function loadDevices() {
  devices.value = await api.get<NetworkDevice[]>("/network/devices", { active_only: false });
}

async function addDevice() {
  await api.post("/network/devices", newDevice.value);
  newDevice.value = { mac_address: "", name: "", device_type: "unknown" };
  await loadDevices();
}

async function toggleActive(d: NetworkDevice) {
  await api.patch(`/network/devices/${d.id}`, { is_active: !d.is_active });
  await loadDevices();
}

async function toggleTrusted(d: NetworkDevice) {
  await api.patch(`/network/devices/${d.id}`, { is_trusted: !d.is_trusted });
  await loadDevices();
}

async function deleteDevice(id: number) {
  await api.delete(`/network/devices/${id}`);
  await loadDevices();
}

async function doLookup() {
  if (!lookupMac.value) return;
  lookupResult.value = await api.get("/network/lookup", { mac: lookupMac.value });
}

const deviceTypes = ["camera", "valve", "sensor", "phone", "laptop", "tablet", "unknown"];

onMounted(loadDevices);
</script>

<template>
  <v-card>
    <v-card-title>MAC-Allowlist</v-card-title>
    <v-card-text>
      <p class="text-body-2 mb-3">
        Kameras und IoT-Geräte prüfen unbekannte MAC-Adressen über diese Liste.
        Aktive und vertrauenswürdige Geräte lösen <strong>keinen</strong> Alarm aus.
      </p>

      <v-row class="mb-4">
        <v-col v-if="auth.isAdmin" cols="12" md="6">
          <v-card variant="outlined" class="pa-3">
            <strong class="d-block mb-2">Gerät hinzufügen</strong>
            <v-text-field
              v-model="newDevice.mac_address"
              label="MAC-Adresse"
              placeholder="AA:BB:CC:DD:EE:FF"
              density="compact"
            />
            <v-text-field
              v-model="newDevice.name"
              label="Name"
              density="compact"
            />
            <v-select
              v-model="newDevice.device_type"
              label="Typ"
              :items="deviceTypes"
              density="compact"
            />
            <v-btn color="primary" block @click="addDevice">Hinzufügen</v-btn>
          </v-card>
        </v-col>
        <v-col cols="12" :md="auth.isAdmin ? 6 : 12">
          <v-card variant="outlined" class="pa-3">
            <strong class="d-block mb-2">Quick-Lookup</strong>
            <v-text-field
              v-model="lookupMac"
              label="MAC-Adresse prüfen"
              placeholder="AA:BB:CC:DD:EE:FF"
              density="compact"
              @keyup.enter="doLookup"
            >
              <template #append>
                <v-btn variant="text" @click="doLookup">Check</v-btn>
              </template>
            </v-text-field>
            <v-alert
              v-if="lookupResult"
              :type="lookupResult.is_trusted ? 'success' : 'warning'"
              density="compact"
              class="mt-2"
            >
              <strong>{{ lookupResult.mac_address }}</strong> –
              {{
                lookupResult.is_trusted
                  ? `vertrauenswürdig (${lookupResult.device_name ?? "unbenannt"})`
                  : lookupResult.is_active
                    ? "unbekannt (Alarm!)"
                    : "inaktiv"
              }}
            </v-alert>
          </v-card>
        </v-col>
      </v-row>

      <v-table>
        <thead>
          <tr>
            <th>MAC</th>
            <th>Name</th>
            <th>Typ</th>
            <th>Vertraut</th>
            <th>Aktiv</th>
            <th class="text-right">Aktion</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in devices" :key="d.id">
            <td><code>{{ d.mac_address }}</code></td>
            <td>{{ d.name }}</td>
            <td><v-chip size="x-small">{{ d.device_type }}</v-chip></td>
            <td>
              <v-switch
                :model-value="d.is_trusted"
                color="success"
                density="compact"
                hide-details
                :disabled="!auth.isAdmin"
                @update:model-value="toggleTrusted(d)"
              />
            </td>
            <td>
              <v-switch
                :model-value="d.is_active"
                color="primary"
                density="compact"
                hide-details
                :disabled="!auth.isAdmin"
                @update:model-value="toggleActive(d)"
              />
            </td>
            <td class="text-right">
              <v-btn
                v-if="auth.isAdmin"
                size="small"
                icon="mdi-delete"
                color="error"
                variant="text"
                @click="deleteDevice(d.id)"
              />
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card-text>
  </v-card>
</template>
