<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface ApiKey {
  id: number;
  name: string;
  description: string | null;
  key_prefix: string;
  owner_user_id: number;
  owner_username: string | null;
  scopes: string[];
  allowed_ips: string[] | null;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  use_count: number;
}

interface ApiKeyCreated extends ApiKey {
  api_key: string;
}

interface ScopeDef {
  scope: string;
  label: string;
  description?: string;
}

interface ScopeGroup {
  key: string;
  label: string;
  icon: string;
  scopes: ScopeDef[];
}

interface ScopeCatalog {
  groups: ScopeGroup[];
  all_scopes: string[];
}

const keys = ref<ApiKey[]>([]);
const catalog = ref<ScopeCatalog | null>(null);
const loading = ref(false);
const tab = ref<"list" | "create">("list");

// Form
const showCreateDialog = ref(false);
const newKey = ref<ApiKeyCreated | null>(null);
const form = ref({
  name: "",
  description: "",
  scopes: [] as string[],
  allowed_ips: "" as string, // comma-separated
  expires_in_days: null as number | null,
});

async function loadKeys() {
  loading.value = true;
  try {
    keys.value = await api.get<ApiKey[]>("/keys/");
  } finally {
    loading.value = false;
  }
}

async function loadCatalog() {
  catalog.value = await api.get<ScopeCatalog>("/keys/catalog");
}

function openCreate() {
  form.value = {
    name: "",
    description: "",
    scopes: [],
    allowed_ips: "",
    expires_in_days: 365,
  };
  newKey.value = null;
  showCreateDialog.value = true;
}

function toggleScope(scope: string) {
  const idx = form.value.scopes.indexOf(scope);
  if (idx >= 0) form.value.scopes.splice(idx, 1);
  else form.value.scopes.push(scope);
}

function selectPreset(preset: "readonly" | "uploader" | "admin" | "iot-device") {
  if (!catalog.value) return;
  form.value.scopes = [];

  if (preset === "readonly") {
    for (const g of catalog.value.groups) {
      for (const s of g.scopes) {
        if (s.scope.endsWith(":read")) form.value.scopes.push(s.scope);
      }
    }
  } else if (preset === "uploader") {
    form.value.scopes = ["cameras:upload"];
  } else if (preset === "admin") {
    form.value.scopes = ["*"];
  } else if (preset === "iot-device") {
    form.value.scopes = [
      "devices:heartbeat",
      "devices:events",
      "cameras:upload",
      "valves:poll",
      "network:read",
    ];
  }
}

async function submitCreate() {
  const payload: Record<string, unknown> = {
    name: form.value.name,
    scopes: form.value.scopes,
  };
  if (form.value.description) payload.description = form.value.description;
  if (form.value.allowed_ips.trim()) {
    payload.allowed_ips = form.value.allowed_ips
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
  }
  if (form.value.expires_in_days) {
    payload.expires_in_days = form.value.expires_in_days;
  }

  newKey.value = await api.post<ApiKeyCreated>("/keys/", payload);
  showCreateDialog.value = false;
  await loadKeys();
}

async function rotate(k: ApiKey) {
  if (!confirm(`Schlüssel "${k.name}" rotieren? Der alte wird ungültig.`)) return;
  const result = await api.post<ApiKeyCreated>(`/keys/${k.id}/rotate`, {});
  newKey.value = result;
  await loadKeys();
}

async function toggleActive(k: ApiKey) {
  await api.patch(`/keys/${k.id}`, { is_active: !k.is_active });
  await loadKeys();
}

async function deleteKey(k: ApiKey) {
  if (!confirm(`Schlüssel "${k.name}" wirklich löschen?`)) return;
  await api.delete(`/keys/${k.id}`);
  await loadKeys();
}

async function selfCheck(k: ApiKey) {
  const scopesToTest = ["cameras:upload", "finance:write", "valves:command", "*"];
  const result = await api.post<{
    allowed: string[];
    missing: string[];
  }>(`/keys/${k.id}/check`, { scopes: scopesToTest });
  alert(
    `Erlaubt: ${result.allowed.join(", ") || "(keine)"}\n` +
    `Fehlend: ${result.missing.join(", ") || "(keine)"}`,
  );
}

function copyAndClose() {
  if (!newKey.value) return;
  const text = newKey.value.api_key;
  // navigator.clipboard may not exist in non-HTTPS contexts or tests.
  const nav = typeof navigator !== "undefined" ? navigator : undefined;
  if (nav?.clipboard?.writeText) {
    nav.clipboard.writeText(text).catch(() => {
      /* ignore */
    });
  }
  newKey.value = null;
}

function isScopeSelected(scope: string) {
  if (form.value.scopes.includes("*")) return true;
  if (form.value.scopes.includes(scope)) return true;
  // Match resource wildcard
  if (form.value.scopes.some((s) => s.endsWith(":*") && scope.startsWith(s.slice(0, -1)))) {
    return true;
  }
  return false;
}

function scopeClass(scope: string) {
  if (form.value.scopes.includes("*")) return "text-success";
  if (form.value.scopes.includes(scope)) return "text-success";
  if (form.value.scopes.some((s) => s.endsWith(":*") && scope.startsWith(s.slice(0, -1)))) {
    return "text-success";
  }
  return "text-medium-emphasis";
}

const groupedScopes = computed(() => catalog.value?.groups ?? []);

onMounted(async () => {
  await Promise.all([loadKeys(), loadCatalog()]);
});
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">API-Schlüssel</h1>
    <p class="text-body-2 mb-4">
      Erstelle fein granulare API-Schlüssel mit spezifischen Berechtigungen
      (Scopes), IP-Allowlist und Ablaufdatum.
    </p>

    <v-tabs v-model="tab" color="primary" class="mb-4">
      <v-tab value="list">
        <v-icon start>mdi-key</v-icon>
        Schlüssel ({{ keys.length }})
      </v-tab>
      <v-tab value="create" @click="openCreate">
        <v-icon start>mdi-plus</v-icon>
        Neu erstellen
      </v-tab>
    </v-tabs>

    <v-window v-model="tab">
      <!-- ── LIST ──────────────────────────────────────────────── -->
      <v-window-item value="list">
        <v-skeleton-loader v-if="loading" type="table" />
        <v-card v-else>
          <v-table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Prefix</th>
                <th>Owner</th>
                <th>Scopes</th>
                <th>IPs</th>
                <th>Ablauf</th>
                <th>Nutzung</th>
                <th>Status</th>
                <th class="text-right">Aktionen</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="k in keys" :key="k.id">
                <td>
                  <strong>{{ k.name }}</strong>
                  <div v-if="k.description" class="text-caption">
                    {{ k.description }}
                  </div>
                </td>
                <td><code>{{ k.key_prefix }}…</code></td>
                <td>{{ k.owner_username ?? `#${k.owner_user_id}` }}</td>
                <td>
                  <v-chip
                    v-for="s in k.scopes.slice(0, 3)"
                    :key="s"
                    size="x-small"
                    class="me-1 mb-1"
                  >
                    {{ s }}
                  </v-chip>
                  <span v-if="k.scopes.length > 3" class="text-caption">
                    +{{ k.scopes.length - 3 }}
                  </span>
                </td>
                <td>
                  <span v-if="!k.allowed_ips || k.allowed_ips.length === 0" class="text-caption">—</span>
                  <v-chip v-for="ip in k.allowed_ips" :key="ip" size="x-small" class="me-1">
                    {{ ip }}
                  </v-chip>
                </td>
                <td>
                  <span v-if="!k.expires_at" class="text-caption">nie</span>
                  <span v-else-if="new Date(k.expires_at) < new Date()" class="text-error">
                    abgelaufen
                  </span>
                  <span v-else>
                    {{ new Date(k.expires_at).toLocaleDateString("de-DE") }}
                  </span>
                </td>
                <td>
                  <span class="text-caption">{{ k.use_count }}×</span>
                  <div v-if="k.last_used_at" class="text-caption text-medium-emphasis">
                    {{ new Date(k.last_used_at).toLocaleDateString("de-DE") }}
                  </div>
                </td>
                <td>
                  <v-chip :color="k.is_active ? 'success' : 'grey'" size="small">
                    {{ k.is_active ? "aktiv" : "inaktiv" }}
                  </v-chip>
                </td>
                <td class="text-right">
                  <v-btn
                    size="small"
                    icon="mdi-cached"
                    variant="text"
                    title="Rotieren"
                    @click="rotate(k)"
                  />
                  <v-btn
                    size="small"
                    icon="mdi-test-tube"
                    variant="text"
                    title="Scopes testen"
                    @click="selfCheck(k)"
                  />
                  <v-btn
                    size="small"
                    :icon="k.is_active ? 'mdi-pause' : 'mdi-play'"
                    :color="k.is_active ? 'warning' : 'success'"
                    variant="text"
                    @click="toggleActive(k)"
                  />
                  <v-btn
                    size="small"
                    icon="mdi-delete"
                    color="error"
                    variant="text"
                    @click="deleteKey(k)"
                  />
                </td>
              </tr>
            </tbody>
          </v-table>
        </v-card>
      </v-window-item>

      <!-- ── CREATE ────────────────────────────────────────────── -->
      <v-window-item value="create">
        <v-card>
          <v-card-text>
            <p class="text-body-2 mb-4">
              Wähle einen Namen und die gewünschten Scopes. Der Key wird
              <strong>einmal</strong> angezeigt – sicher kopieren!
            </p>

            <v-text-field
              v-model="form.name"
              label="Name"
              placeholder="z.B. Pi Cam Upload Key"
            />
            <v-textarea
              v-model="form.description"
              label="Beschreibung (optional)"
              rows="2"
            />
            <v-text-field
              v-model="form.allowed_ips"
              label="Erlaubte IPs / CIDR (optional, komma-getrennt)"
              placeholder="z.B. 192.168.1.0/24, 10.0.0.5"
              hint="Leer = alle IPs erlaubt"
            />
            <v-text-field
              v-model.number="form.expires_in_days"
              label="Gültig für X Tage (leer = kein Ablauf)"
              type="number"
            />

            <v-divider class="my-4" />

            <div class="d-flex align-center mb-3">
              <strong>Berechtigungen (Scopes)</strong>
              <v-spacer />
              <v-menu>
                <template #activator="{ props }">
                  <v-btn
                    v-bind="props"
                    size="small"
                    prepend-icon="mdi-flash"
                    variant="tonal"
                  >
                    Presets
                  </v-btn>
                </template>
                <v-list>
                  <v-list-item @click="selectPreset('readonly')">
                    <v-list-item-title>Read-only</v-list-item-title>
                    <v-list-item-subtitle>Alle :read Scopes</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item @click="selectPreset('uploader')">
                    <v-list-item-title>Nur Bild-Upload</v-list-item-title>
                    <v-list-item-subtitle>cameras:upload</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item @click="selectPreset('iot-device')">
                    <v-list-item-title>IoT-Gerät</v-list-item-title>
                    <v-list-item-subtitle>heartbeat + events + upload + poll + network</v-list-item-subtitle>
                  </v-list-item>
                  <v-list-item @click="selectPreset('admin')">
                    <v-list-item-title>Admin (Vollzugriff)</v-list-item-title>
                    <v-list-item-subtitle>*</v-list-item-subtitle>
                  </v-list-item>
                </v-list>
              </v-menu>
            </div>

            <v-row dense>
              <v-col
                v-for="g in groupedScopes"
                :key="g.key"
                cols="12"
                md="6"
              >
                <v-card variant="outlined" class="pa-3 mb-3">
                  <div class="d-flex align-center mb-2">
                    <v-icon size="small" class="me-2">{{ g.icon }}</v-icon>
                    <strong>{{ g.label }}</strong>
                  </div>
                  <v-checkbox
                    v-for="s in g.scopes"
                    :key="s.scope"
                    :model-value="isScopeSelected(s.scope)"
                    :label="`${s.label} – ${s.scope}`"
                    density="compact"
                    hide-details
                    class="mb-1"
                    :class="scopeClass(s.scope)"
                    @update:model-value="toggleScope(s.scope)"
                  />
                  <div
                    v-for="s in g.scopes"
                    :key="`${s.scope}-desc`"
                    class="text-caption text-medium-emphasis ml-8 mb-2"
                  >
                    {{ s.description }}
                  </div>
                </v-card>
              </v-col>
            </v-row>

            <v-alert
              v-if="form.scopes.includes('*')"
              type="warning"
              class="mt-4"
              variant="tonal"
            >
              Der Wildcard-Scope <code>*</code> gewährt <strong>jede</strong>
              Berechtigung – auch zukünftige. Vorsichtig verwenden!
            </v-alert>
          </v-card-text>
          <v-card-actions>
            <v-spacer />
            <v-btn variant="text" @click="tab = 'list'">Abbrechen</v-btn>
            <v-btn
              color="primary"
              :disabled="!form.name || form.scopes.length === 0"
              @click="submitCreate"
            >
              Schlüssel erstellen
            </v-btn>
          </v-card-actions>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- ── Show key once ─────────────────────────────────────── -->
    <v-dialog
      :model-value="newKey !== null"
      max-width="700"
      persistent
      @update:model-value="(v) => { if (!v) newKey = null; }"
    >
      <v-card v-if="newKey">
        <v-card-title class="text-warning">
          ⚠ API-Key – bitte sofort kopieren!
        </v-card-title>
        <v-card-text>
          <p>
            Der Key wird <strong>nur einmal</strong> angezeigt. Prefix:
            <code>{{ newKey.key_prefix }}</code>
          </p>
          <v-text-field
            :model-value="newKey.api_key"
            readonly
            class="mt-3"
            density="compact"
          />
          <v-alert
            type="info"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            Scopes: {{ newKey.scopes.join(", ") }}
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn
            color="primary"
            @click="copyAndClose"
          >
            Kopieren & Schließen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
