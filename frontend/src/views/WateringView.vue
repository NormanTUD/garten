<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";

interface WateringEvent {
  id: number;
  user: { id: number; display_name: string };
  bed: { id: number; name: string } | null;
  started_at: string;
  duration_minutes: number | null;
  water_amount_liters: number | null;
  method: string;
  notes: string | null;
}

const events = ref<WateringEvent[]>([]);
const loading = ref(true);
const showDialog = ref(false);

const form = ref({
  started_at: new Date().toISOString().slice(0, 16),
  duration_minutes: null as number | null,
  water_amount_liters: null as number | null,
  method: "manual",
  notes: "",
});

onMounted(() => loadData());

async function loadData() {
  loading.value = true;
  try {
    events.value = await api.get<WateringEvent[]>("/watering/");
  } finally {
    loading.value = false;
  }
}

function openDialog() {
  form.value = {
    started_at: new Date().toISOString().slice(0, 16),
    duration_minutes: null,
    water_amount_liters: null,
    method: "manual",
    notes: "",
  };
  showDialog.value = true;
}

async function saveEvent() {
  const data: any = {
    ...form.value,
    started_at: new Date(form.value.started_at).toISOString(),
  };
  if (!data.notes) delete data.notes;
  if (!data.duration_minutes) delete data.duration_minutes;
  if (!data.water_amount_liters) delete data.water_amount_liters;
  await api.post("/watering/", data);
  showDialog.value = false;
  await loadData();
}

async function deleteEvent(id: number) {
  await api.delete(`/watering/${id}`);
  await loadData();
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("de-DE", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">Bewässerung</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog">
        Neuer Eintrag
      </v-btn>
    </div>

    <v-skeleton-loader v-if="loading" type="table" />

    <div v-else-if="events.length === 0" class="text-center py-12">
      <v-icon icon="mdi-water-off" size="80" color="grey" />
      <p class="text-h6 text-grey mt-4">Noch keine Bewässerung erfasst</p>
    </div>

    <v-card v-else>
      <v-list>
        <v-list-item
          v-for="event in events"
          :key="event.id"
          :subtitle="event.notes || undefined"
        >
          <template #prepend>
            <v-avatar color="info" variant="tonal">
              <v-icon icon="mdi-water" />
            </v-avatar>
          </template>

          <template #title>
            <span class="font-weight-bold">{{ formatDateTime(event.started_at) }}</span>
            <v-chip v-if="event.duration_minutes" size="small" class="ml-2">{{ event.duration_minutes }} min</v-chip>
            <v-chip v-if="event.water_amount_liters" size="small" class="ml-1">{{ event.water_amount_liters }} L</v-chip>
            <v-chip v-if="event.bed" size="small" variant="outlined" class="ml-1">{{ event.bed.name }}</v-chip>
          </template>

          <template #append>
            <v-chip size="small" variant="text">{{ event.user.display_name }}</v-chip>
            <v-btn size="small" icon="mdi-delete" variant="text" color="error" @click="deleteEvent(event.id)" />
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Watering Dialog -->
    <v-dialog v-model="showDialog" max-width="500">
      <v-card>
        <v-card-title>Bewässerung erfassen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEvent">
            <v-text-field v-model="form.started_at" label="Zeitpunkt *" type="datetime-local" class="mb-2" />
            <v-row>
              <v-col cols="6">
                <v-text-field v-model.number="form.duration_minutes" label="Dauer (min)" type="number" min="0" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model.number="form.water_amount_liters" label="Menge (Liter)" type="number" min="0" step="0.5" />
              </v-col>
            </v-row>
            <v-radio-group v-model="form.method" inline label="Methode" class="mb-2">
              <v-radio label="Manuell" value="manual" />
              <v-radio label="Automatisch" value="automatic" />
            </v-radio-group>
            <v-textarea v-model="form.notes" label="Notizen" rows="2" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!form.started_at" @click="saveEvent">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

