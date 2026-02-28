<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

// ─── Types ────────────────────────────────────────────────

interface DutyConfig {
  id: number;
  year: number;
  total_hours: number;
  hourly_rate_cents: number;
  notes: string | null;
}

interface DutyAssignment {
  id: number;
  user_id: number;
  year: number;
  assigned_hours: number;
  notes: string | null;
  display_name: string;
}

interface DutyLog {
  id: number;
  user_id: number;
  date: string;
  hours: number;
  description: string;
  confirmed: boolean;
  confirmed_by_id: number | null;
  display_name: string;
  confirmed_by_name: string | null;
}

interface DutyMemberBalance {
  user_id: number;
  display_name: string;
  assigned_hours: number;
  confirmed_hours: number;
  pending_hours: number;
  remaining_hours: number;
  compensation_cents: number;
}

interface DutyOverview {
  year: number;
  total_hours: number;
  hourly_rate_cents: number;
  total_assigned: number;
  total_unassigned: number;
  member_count: number;
  default_hours_per_member: number;
  member_balances: DutyMemberBalance[];
}

interface UserOption {
  id: number;
  display_name: string;
}

// ─── State ────────────────────────────────────────────────

const loading = ref(true);
const overview = ref<DutyOverview | null>(null);
const logs = ref<DutyLog[]>([]);
const assignments = ref<DutyAssignment[]>([]);
const configs = ref<DutyConfig[]>([]);
const users = ref<UserOption[]>([]);

const currentYear = new Date().getFullYear();
const selectedYear = ref(currentYear);
const yearOptions = [currentYear - 1, currentYear, currentYear + 1];

const tab = ref("overview");

// ─── Dialogs ──────────────────────────────────────────────

const showLogDialog = ref(false);
const logForm = ref({
  date: new Date().toISOString().slice(0, 10),
  hours: 1,
  description: "",
});

const showConfigDialog = ref(false);
const configForm = ref({
  year: currentYear,
  total_hours: 10,
  hourly_rate_cents: 1500,
  notes: "",
});
const editingConfig = ref(false);

const showAssignmentDialog = ref(false);
const assignmentForm = ref({
  user_id: null as number | null,
  year: currentYear,
  assigned_hours: 2.5,
  notes: "",
});
const editingAssignmentId = ref<number | null>(null);

// ─── Computed ─────────────────────────────────────────────

const myBalance = computed(() => {
  if (!overview.value || !auth.user) return null;
  return overview.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
});

const myLogs = computed(() => {
  if (!auth.user) return [];
  return logs.value.filter((l) => l.user_id === auth.user!.id);
});

const pendingLogs = computed(() => logs.value.filter((l) => !l.confirmed));

// ─── Helpers ──────────────────────────────────────────────

function eur(cents: number): string {
  return (cents / 100).toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  });
}

function hoursLabel(h: number): string {
  if (h === 1) return "1 Stunde";
  return `${h} Stunden`;
}

function progressColor(remaining: number): string {
  if (remaining <= 0) return "success";
  if (remaining <= 1) return "warning";
  return "error";
}

function progressPercent(balance: DutyMemberBalance): number {
  if (balance.assigned_hours === 0) return 100;
  return Math.min(100, Math.round((balance.confirmed_hours / balance.assigned_hours) * 100));
}

// ─── API Calls ────────────────────────────────────────────

async function fetchAll() {
  loading.value = true;
  try {
    const [overviewData, logsData, assignmentsData, configsData] = await Promise.all([
      api.get<DutyOverview>(`/duty/overview/${selectedYear.value}`).catch(() => null),
      api.get<DutyLog[]>(`/duty/logs/${selectedYear.value}`),
      api.get<DutyAssignment[]>(`/duty/assignments/${selectedYear.value}`),
      api.get<DutyConfig[]>("/duty/config"),
    ]);
    overview.value = overviewData;
    logs.value = logsData;
    assignments.value = assignmentsData;
    configs.value = configsData;

    if (auth.isAdmin && users.value.length === 0) {
      users.value = await api.get<UserOption[]>("/users/");
    }
  } catch (e) {
    console.error("Failed to fetch duty data", e);
  } finally {
    loading.value = false;
  }
}

// ─── Log CRUD ─────────────────────────────────────────────

function openLogDialog() {
  logForm.value = {
    date: new Date().toISOString().slice(0, 10),
    hours: 1,
    description: "",
  };
  showLogDialog.value = true;
}

async function submitLog() {
  await api.post("/duty/logs", logForm.value);
  showLogDialog.value = false;
  await fetchAll();
}

async function confirmLog(logId: number) {
  await api.post(`/duty/logs/${logId}/confirm`);
  await fetchAll();
}

async function unconfirmLog(logId: number) {
  await api.post(`/duty/logs/${logId}/unconfirm`);
  await fetchAll();
}

async function deleteLog(logId: number) {
  if (!confirm("Eintrag wirklich löschen?")) return;
  await api.delete(`/duty/logs/${logId}`);
  await fetchAll();
}

// ─── Config CRUD ──────────────────────────────────────────

function openConfigDialog(existing?: DutyConfig) {
  if (existing) {
    editingConfig.value = true;
    configForm.value = {
      year: existing.year,
      total_hours: existing.total_hours,
      hourly_rate_cents: existing.hourly_rate_cents,
      notes: existing.notes || "",
    };
  } else {
    editingConfig.value = false;
    configForm.value = {
      year: selectedYear.value,
      total_hours: 10,
      hourly_rate_cents: 1500,
      notes: "",
    };
  }
  showConfigDialog.value = true;
}

async function submitConfig() {
  if (editingConfig.value) {
    await api.put(`/duty/config/${configForm.value.year}`, {
      total_hours: configForm.value.total_hours,
      hourly_rate_cents: configForm.value.hourly_rate_cents,
      notes: configForm.value.notes || null,
    });
  } else {
    await api.post("/duty/config", configForm.value);
  }
  showConfigDialog.value = false;
  await fetchAll();
}

async function deleteConfig(year: number) {
  if (!confirm(`Konfiguration für ${year} wirklich löschen?`)) return;
  await api.delete(`/duty/config/${year}`);
  await fetchAll();
}

// ─── Assignment CRUD ──────────────────────────────────────

function openAssignmentDialog(existing?: DutyAssignment) {
  if (existing) {
    editingAssignmentId.value = existing.id;
    assignmentForm.value = {
      user_id: existing.user_id,
      year: existing.year,
      assigned_hours: existing.assigned_hours,
      notes: existing.notes || "",
    };
  } else {
    editingAssignmentId.value = null;
    assignmentForm.value = {
      user_id: null,
      year: selectedYear.value,
      assigned_hours: overview.value?.default_hours_per_member || 2.5,
      notes: "",
    };
  }
  showAssignmentDialog.value = true;
}

async function submitAssignment() {
  if (editingAssignmentId.value) {
    await api.put(`/duty/assignments/${editingAssignmentId.value}`, {
      assigned_hours: assignmentForm.value.assigned_hours,
      notes: assignmentForm.value.notes || null,
    });
  } else {
    await api.post("/duty/assignments", assignmentForm.value);
  }
  showAssignmentDialog.value = false;
  await fetchAll();
}

async function deleteAssignment(id: number) {
  if (!confirm("Zuweisung wirklich löschen?")) return;
  await api.delete(`/duty/assignments/${id}`);
  await fetchAll();
}

async function autoAssign() {
  if (!confirm(`Stunden für ${selectedYear.value} gleichmäßig aufteilen? Bestehende Zuweisungen werden überschrieben.`)) return;
  await api.post(`/duty/assignments/${selectedYear.value}/auto-assign`);
  await fetchAll();
}

// ─── Lifecycle ────────────────────────────────────────────

onMounted(fetchAll);
watch(selectedYear, fetchAll);
</script>

<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-2 flex-wrap ga-2">
      <h1 class="text-h4">Gartenstunden</h1>
      <v-spacer />
      <v-btn-toggle v-model="selectedYear" mandatory color="primary" density="compact" variant="outlined">
        <v-btn v-for="y in yearOptions" :key="y" :value="y" size="small"
          :variant="y === selectedYear ? 'flat' : 'outlined'">{{ y }}</v-btn>
      </v-btn-toggle>
    </div>

    <v-skeleton-loader v-if="loading" type="card@2" />

    <template v-else>
      <!-- No config warning -->
      <v-alert v-if="!overview" type="info" variant="tonal" class="mb-4">
        <div class="d-flex align-center">
          <div>
            Für {{ selectedYear }} ist noch keine Gartenstunden-Konfiguration hinterlegt.
            <span v-if="auth.isAdmin">Erstelle eine, um loszulegen.</span>
            <span v-else>Bitte einen Admin, die Konfiguration anzulegen.</span>
          </div>
          <v-spacer />
          <v-btn v-if="auth.isAdmin" color="primary" @click="openConfigDialog()">Konfiguration erstellen</v-btn>
        </div>
      </v-alert>

      <template v-if="overview">
        <!-- ═══ My Status ═══ -->
        <v-card v-if="myBalance" class="mb-4" :color="progressColor(myBalance.remaining_hours)" variant="tonal">
          <v-card-text class="pa-4">
            <div class="d-flex align-center mb-3">
              <div class="flex-grow-1">
                <div class="text-body-1">Dein Stand {{ selectedYear }}</div>
                <div class="text-h4 font-weight-bold my-1">
                  {{ myBalance.confirmed_hours }} / {{ myBalance.assigned_hours }} Stunden
                </div>
                <div class="text-body-2">
                  <template v-if="myBalance.remaining_hours <= 0">
                    ✓ Alle Stunden abgeleistet!
                    <span v-if="myBalance.confirmed_hours > myBalance.assigned_hours">
                      ({{ (myBalance.confirmed_hours - myBalance.assigned_hours).toFixed(1) }}h extra 🎉)
                    </span>
                  </template>
                  <template v-else>
                    Noch {{ myBalance.remaining_hours }} Stunden offen
                    <span class="text-medium-emphasis">
                      (oder {{ eur(myBalance.compensation_cents) }} Ausgleich)
                    </span>
                  </template>
                </div>
                <div v-if="myBalance.pending_hours > 0" class="text-caption text-warning mt-1">
                  ⏳ {{ myBalance.pending_hours }}h warten auf Bestätigung
                </div>
              </div>
              <v-btn color="primary" size="large" prepend-icon="mdi-plus" @click="openLogDialog">
                Stunden eintragen
              </v-btn>
            </div>
            <v-progress-linear
              :model-value="progressPercent(myBalance)"
              :color="progressColor(myBalance.remaining_hours)"
              height="12"
              rounded
            >
              <template #default>
                <span class="text-caption font-weight-bold">{{ progressPercent(myBalance) }}%</span>
              </template>
            </v-progress-linear>
          </v-card-text>
        </v-card>

        <!-- ═══ Summary Card ═══ -->
        <v-card class="mb-4">
          <v-card-text>
            <v-row dense>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Gesamt-Pflicht</div>
                <div class="text-h6 font-weight-bold">{{ overview.total_hours }}h</div>
                <div class="text-caption text-medium-emphasis">für den ganzen Garten</div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Pro Person (Standard)</div>
                <div class="text-h6 font-weight-bold">{{ overview.default_hours_per_member }}h</div>
                <div class="text-caption text-medium-emphasis">{{ overview.member_count }} Mitglieder</div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Stundensatz</div>
                <div class="text-h6 font-weight-bold">{{ eur(overview.hourly_rate_cents) }}</div>
                <div class="text-caption text-medium-emphasis">Ausgleichszahlung</div>
              </v-col>
              <v-col cols="6" sm="3">
                <div class="text-caption text-medium-emphasis">Nicht zugewiesen</div>
                <div class="text-h6 font-weight-bold" :class="overview.total_unassigned > 0 ? 'text-warning' : 'text-success'">
                  {{ overview.total_unassigned }}h
                </div>
                <div class="text-caption text-medium-emphasis">
                  {{ overview.total_unassigned > 0 ? 'noch aufzuteilen' : 'alles verteilt ✓' }}
                </div>
              </v-col>
            </v-row>
          </v-card-text>

          <!-- All members progress -->
          <v-divider />
          <v-card-text>
            <div class="text-subtitle-2 font-weight-bold mb-3">Alle Mitglieder</div>
            <div v-for="b in overview.member_balances" :key="b.user_id" class="mb-3">
              <div class="d-flex align-center mb-1">
                <span class="text-body-2 font-weight-bold" style="min-width: 120px;">{{ b.display_name }}</span>
                <v-spacer />
                <span class="text-body-2">
                  {{ b.confirmed_hours }} / {{ b.assigned_hours }}h
                </span>
                <v-chip v-if="b.pending_hours > 0" size="x-small" color="warning" variant="flat" class="ml-2">
                  +{{ b.pending_hours }}h ⏳
                </v-chip>
                <v-chip v-if="b.remaining_hours < 0" size="x-small" color="success" variant="flat" class="ml-2">
                  +{{ Math.abs(b.remaining_hours) }}h extra 🎉
                </v-chip>
                <v-chip v-else-if="b.remaining_hours === 0" size="x-small" color="success" variant="flat" class="ml-2">
                  ✓
                </v-chip>
                <v-chip v-else-if="b.compensation_cents > 0" size="x-small" color="error" variant="tonal" class="ml-2">
                  {{ eur(b.compensation_cents) }} offen
                </v-chip>
              </div>
              <v-progress-linear
                :model-value="progressPercent(b)"
                :color="progressColor(b.remaining_hours)"
                height="8"
                rounded
              />
            </div>
          </v-card-text>
        </v-card>

        <!-- ═══ Tabs ═══ -->
        <v-tabs v-model="tab" color="primary" class="mb-4">
          <v-tab value="overview">
            <v-icon start icon="mdi-clipboard-list" />Einträge ({{ logs.length }})
          </v-tab>
          <v-tab v-if="auth.isAdmin" value="assignments">
            <v-icon start icon="mdi-account-group" />Zuweisungen ({{ assignments.length }})
          </v-tab>
          <v-tab v-if="auth.isAdmin" value="config">
            <v-icon start icon="mdi-cog" />Konfiguration
          </v-tab>
        </v-tabs>

        <v-window v-model="tab">
          <!-- ─── Logs Tab ─── -->
          <v-window-item value="overview">
            <div class="d-flex ga-2 mb-4">
              <v-btn color="primary" prepend-icon="mdi-plus" @click="openLogDialog">Stunden eintragen</v-btn>
            </div>

            <div v-if="logs.length === 0" class="text-center py-8">
              <v-icon icon="mdi-clock-outline" size="64" color="grey" />
              <p class="text-body-1 text-grey mt-2">Noch keine Einträge für {{ selectedYear }}</p>
            </div>

            <v-list v-else lines="three">
              <v-list-item v-for="log in logs" :key="log.id">
                <template #prepend>
                  <v-avatar :color="log.confirmed ? 'success' : 'warning'" variant="tonal" size="48">
                    <v-icon :icon="log.confirmed ? 'mdi-check-circle' : 'mdi-clock-outline'" />
                  </v-avatar>
                </template>
                <template #title>
                  <span class="font-weight-bold">{{ log.display_name }}</span>
                  <v-chip size="x-small" class="ml-2" variant="tonal">{{ log.hours }}h</v-chip>
                  <v-chip v-if="log.confirmed" size="x-small" color="success" variant="flat" class="ml-1">
                    ✓ {{ log.confirmed_by_name }}
                  </v-chip>
                  <v-chip v-else size="x-small" color="warning" variant="flat" class="ml-1">
                    ⏳ unbestätigt
                  </v-chip>
                </template>
                <template #subtitle>
                  {{ new Date(log.date).toLocaleDateString("de-DE") }} · {{ log.description }}
                </template>
                <template #append>
                  <div class="d-flex ga-1">
                    <v-btn v-if="auth.isAdmin && !log.confirmed" size="x-small" color="success" variant="tonal"
                      @click="confirmLog(log.id)">✓ Bestätigen</v-btn>
                    <v-btn v-if="auth.isAdmin && log.confirmed" size="x-small" color="warning" variant="tonal"
                      @click="unconfirmLog(log.id)">↩ Widerrufen</v-btn>
                    <v-btn v-if="auth.isAdmin" size="x-small" icon="mdi-delete" variant="text" color="error"
                      @click="deleteLog(log.id)" />
                  </div>
                </template>
              </v-list-item>
            </v-list>
          </v-window-item>

          <!-- ─── Assignments Tab (Admin) ─── -->
          <v-window-item value="assignments">
            <div class="d-flex ga-2 mb-4">
              <v-btn color="primary" prepend-icon="mdi-plus" @click="openAssignmentDialog()">Zuweisung</v-btn>
              <v-btn color="info" variant="tonal" prepend-icon="mdi-auto-fix" @click="autoAssign">
                Gleichmäßig aufteilen
              </v-btn>
            </div>

            <div v-if="assignments.length === 0" class="text-center py-8">
              <v-icon icon="mdi-account-group-outline" size="64" color="grey" />
              <p class="text-body-1 text-grey mt-2">Keine Zuweisungen. Klicke "Gleichmäßig aufteilen" um zu starten.</p>
            </div>

            <v-list v-else lines="two">
              <v-list-item v-for="a in assignments" :key="a.id">
                <template #prepend>
                  <v-avatar color="primary" variant="tonal" size="40">
                    <v-icon icon="mdi-account" />
                  </v-avatar>
                </template>
                <template #title>
                  <span class="font-weight-bold">{{ a.display_name }}</span>
                  <v-chip size="x-small" class="ml-2" variant="tonal">{{ a.assigned_hours }}h</v-chip>
                </template>
                <template #subtitle>
                  <span v-if="a.notes">{{ a.notes }}</span>
                  <span v-else class="text-medium-emphasis">Keine Notiz</span>
                </template>
                <template #append>
                  <v-btn size="x-small" icon="mdi-pencil" variant="text" @click="openAssignmentDialog(a)" />
                  <v-btn size="x-small" icon="mdi-delete" variant="text" color="error" @click="deleteAssignment(a.id)" />
                </template>
              </v-list-item>
            </v-list>
          </v-window-item>

          <!-- ─── Config Tab (Admin) ─── -->
          <v-window-item value="config">
            <div class="d-flex ga-2 mb-4">
              <v-btn color="primary" prepend-icon="mdi-plus" @click="openConfigDialog()">Neues Jahr</v-btn>
            </div>

            <v-table density="compact">
              <thead>
                <tr>
                  <th>Jahr</th>
                  <th class="text-right">Gesamt-Stunden</th>
                  <th class="text-right">Stundensatz</th>
                  <th>Notizen</th>
                  <th style="width: 100px;"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="c in configs" :key="c.id" :class="c.year === selectedYear ? 'bg-primary-lighten-5' : ''">
                  <td class="font-weight-bold">{{ c.year }}</td>
                  <td class="text-right">{{ c.total_hours }}h</td>
                  <td class="text-right">{{ eur(c.hourly_rate_cents) }}/h</td>
                  <td class="text-medium-emphasis">{{ c.notes || "–" }}</td>
                  <td class="text-right">
                    <v-btn size="x-small" icon="mdi-pencil" variant="text" @click="openConfigDialog(c)" />
                    <v-btn size="x-small" icon="mdi-delete" variant="text" color="error" @click="deleteConfig(c.year)" />
                  </td>
                </tr>
                <tr v-if="configs.length === 0">
                  <td colspan="5" class="text-center text-grey py-4">Keine Konfigurationen vorhanden</td>
                </tr>
              </tbody>
            </v-table>
          </v-window-item>
        </v-window>
      </template>
    </template>

    <!-- ═══ Log Dialog ═══ -->
    <v-dialog v-model="showLogDialog" max-width="500">
      <v-card>
        <v-card-title>Gartenstunden eintragen</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="logForm.date"
            label="Datum"
            type="date"
            class="mb-3"
          />
          <v-text-field
            v-model.number="logForm.hours"
            label="Stunden"
            type="number"
            :min="0.5"
            :step="0.5"
            hint="In 0.5h-Schritten"
            persistent-hint
            class="mb-3"
          />
          <v-textarea
            v-model="logForm.description"
            label="Was wurde gemacht? (optional)"
            rows="3"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showLogDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :disabled="logForm.hours <= 0"
            @click="submitLog"
          >
            Eintragen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Config Dialog ═══ -->
    <v-dialog v-model="showConfigDialog" max-width="500">
      <v-card>
        <v-card-title>{{ editingConfig ? 'Konfiguration bearbeiten' : 'Neue Konfiguration' }}</v-card-title>
        <v-card-text>
          <v-text-field
            v-model.number="configForm.year"
            label="Jahr"
            type="number"
            :disabled="editingConfig"
            class="mb-3"
          />
          <v-text-field
            v-model.number="configForm.total_hours"
            label="Gesamt-Stunden (ganzer Garten)"
            type="number"
            :min="1"
            :step="0.5"
            class="mb-3"
          />
          <v-text-field
            v-model.number="configForm.hourly_rate_cents"
            label="Stundensatz (Cent)"
            type="number"
            :min="100"
            :step="100"
            :hint="`= ${eur(configForm.hourly_rate_cents)} pro Stunde`"
            persistent-hint
            class="mb-3"
          />
          <v-textarea
            v-model="configForm.notes"
            label="Notizen (optional)"
            rows="2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showConfigDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" @click="submitConfig">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Assignment Dialog ═══ -->
    <v-dialog v-model="showAssignmentDialog" max-width="500">
      <v-card>
        <v-card-title>{{ editingAssignmentId ? 'Zuweisung bearbeiten' : 'Neue Zuweisung' }}</v-card-title>
        <v-card-text>
          <v-select
            v-model="assignmentForm.user_id"
            :items="users"
            item-title="display_name"
            item-value="id"
            label="Mitglied"
            :disabled="!!editingAssignmentId"
            class="mb-3"
          />
          <v-text-field
            v-model.number="assignmentForm.assigned_hours"
            label="Zugewiesene Stunden"
            type="number"
            :min="0.5"
            :step="0.5"
            class="mb-3"
          />
          <v-textarea
            v-model="assignmentForm.notes"
            label="Notizen (optional, z.B. 'Tausch mit Max')"
            rows="2"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAssignmentDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :disabled="!editingAssignmentId && !assignmentForm.user_id"
            @click="submitAssignment"
          >
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
