<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";

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

const events = ref<TimelineEvent[]>([]);
const loading = ref(false);
const selectedType = ref<string | null>(null);

async function load() {
  loading.value = true;
  try {
    const params: Record<string, string | number> = { limit: 200 };
    if (selectedType.value) params.event_type = selectedType.value;
    const r = await api.get<{ events: TimelineEvent[] }>("/timeline/", params);
    events.value = r.events;
  } finally {
    loading.value = false;
  }
}

const types = [
  { v: null, label: "Alle", icon: "mdi-view-list" },
  { v: "harvest", label: "Ernte", icon: "mdi-basket" },
  { v: "watering", label: "Bewässerung", icon: "mdi-water" },
  { v: "expense", label: "Ausgaben", icon: "mdi-cash-minus" },
  { v: "payment", label: "Einzahlungen", icon: "mdi-cash-plus" },
  { v: "duty_log", label: "Gartenstunden", icon: "mdi-shovel" },
  { v: "message", label: "Nachrichten", icon: "mdi-email" },
  { v: "shopping_added", label: "Einkaufsliste", icon: "mdi-cart" },
  { v: "image_captured", label: "Kamera-Snapshots", icon: "mdi-camera" },
  { v: "valve_opened", label: "Ventile", icon: "mdi-water-pump" },
];

function eventColor(t: string): string {
  if (t.includes("alert")) return "error";
  if (t.includes("expense")) return "red";
  if (t.includes("payment") || t.includes("harvest")) return "success";
  if (t.includes("valve_opened") || t.includes("watering")) return "info";
  return "grey";
}

onMounted(load);
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">Garten-Timeline</h1>
    <p class="text-body-2 mb-4">
      Vereinheitlichte Ansicht über Ernten, Bewässerung, Finanzen, Gartenstunden, Kameras und IoT-Events.
    </p>

    <v-chip-group
      v-model="selectedType"
      mandatory
      selected-class="text-primary"
      class="mb-4"
      @update:model-value="load"
    >
      <v-chip
        v-for="t in types"
        :key="String(t.v)"
        :value="t.v"
      >
        <v-icon start>{{ t.icon }}</v-icon>
        {{ t.label }}
      </v-chip>
    </v-chip-group>

    <v-skeleton-loader v-if="loading" type="list-item-three-line@5" />
    <v-timeline v-else density="comfortable" align="start" side="end">
      <v-timeline-item
        v-for="ev in events"
        :key="ev.id"
        :dot-color="eventColor(ev.event_type)"
        size="small"
      >
        <template #opposite>
          <span class="text-caption text-medium-emphasis">
            {{ new Date(ev.occurred_at).toLocaleString("de-DE") }}
          </span>
        </template>
        <div>
          <strong>{{ ev.title }}</strong>
          <span v-if="ev.actor_name" class="text-caption">
            — {{ ev.actor_name }}
          </span>
        </div>
        <div class="text-body-2 text-medium-emphasis">{{ ev.summary }}</div>
      </v-timeline-item>
    </v-timeline>
  </div>
</template>
