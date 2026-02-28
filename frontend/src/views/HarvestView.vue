<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";

interface Harvest {
  id: number;
  user: { id: number; display_name: string };
  bed: { id: number; name: string } | null;
  plant: { id: number; name: string; variety: string | null } | null;
  amount: number;
  unit: string;
  quality_rating: number | null;
  harvest_date: string;
  notes: string | null;
}

interface Plant {
  id: number;
  name: string;
  variety: string | null;
}

const harvests = ref<Harvest[]>([]);
const plants = ref<Plant[]>([]);
const loading = ref(true);
const showDialog = ref(false);

const unitOptions = [
  { title: "Kilogramm", value: "kg" },
  { title: "Gramm", value: "g" },
  { title: "Stück", value: "stueck" },
  { title: "Bund", value: "bund" },
  { title: "Liter", value: "liter" },
  { title: "Eimer", value: "eimer" },
];

const form = ref({
  plant_id: undefined as number | undefined,
  amount: null as number | null,
  unit: "kg",
  quality_rating: undefined as number | undefined,
  harvest_date: new Date().toISOString().split("T")[0],
  notes: "",
});

onMounted(() => loadData());

async function loadData() {
  loading.value = true;
  try {
    [harvests.value, plants.value] = await Promise.all([
      api.get<Harvest[]>("/harvests/"),
      api.get<Plant[]>("/plants/"),
    ]);
  } finally {
    loading.value = false;
  }
}

function plantLabel(plant: Plant): string {
  return plant.variety ? `${plant.name} (${plant.variety})` : plant.name;
}

function openDialog() {
  form.value = {
    plant_id: undefined,
    amount: null,
    unit: "kg",
    quality_rating: undefined,
    harvest_date: new Date().toISOString().split("T")[0],
    notes: "",
  };
  showDialog.value = true;
}

async function saveHarvest() {
  const data: any = { ...form.value };
  if (!data.plant_id) delete data.plant_id;
  if (!data.notes) delete data.notes;
  if (!data.quality_rating) delete data.quality_rating;
  await api.post("/harvests/", data);
  showDialog.value = false;
  await loadData();
}

async function deleteHarvest(id: number) {
  await api.delete(`/harvests/${id}`);
  await loadData();
}

function formatUnit(unit: string): string {
  const map: Record<string, string> = { kg: "kg", g: "g", stueck: "Stk", bund: "Bund", liter: "L", eimer: "Eimer" };
  return map[unit] || unit;
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">Ernte</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openDialog">
        Neue Ernte
      </v-btn>
    </div>

    <v-skeleton-loader v-if="loading" type="table" />

    <div v-else-if="harvests.length === 0" class="text-center py-12">
      <v-icon icon="mdi-basket-outline" size="80" color="grey" />
      <p class="text-h6 text-grey mt-4">Noch keine Ernten erfasst</p>
    </div>

    <v-card v-else>
      <v-list>
        <v-list-item
          v-for="harvest in harvests"
          :key="harvest.id"
          :subtitle="harvest.harvest_date + (harvest.notes ? ' – ' + harvest.notes : '')"
        >
          <template #prepend>
            <v-avatar color="success" variant="tonal">
              <v-icon icon="mdi-basket" />
            </v-avatar>
          </template>

          <template #title>
            <span class="font-weight-bold">{{ harvest.amount }} {{ formatUnit(harvest.unit) }}</span>
            <span v-if="harvest.plant"> – {{ harvest.plant.name }}</span>
            <v-rating
              v-if="harvest.quality_rating"
              :model-value="harvest.quality_rating"
              density="compact"
              size="small"
              readonly
              class="ml-2 d-inline-flex"
            />
          </template>

          <template #append>
            <v-chip size="small" variant="text">{{ harvest.user.display_name }}</v-chip>
            <v-btn size="small" icon="mdi-delete" variant="text" color="error" @click="deleteHarvest(harvest.id)" />
          </template>
        </v-list-item>
      </v-list>
    </v-card>

    <!-- Harvest Dialog -->
    <v-dialog v-model="showDialog" max-width="500">
      <v-card>
        <v-card-title>Neue Ernte erfassen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveHarvest">
            <v-select
              v-model="form.plant_id"
              label="Pflanze"
              :items="plants"
              :item-title="plantLabel"
              item-value="id"
              clearable
              class="mb-2"
            />
            <v-row>
              <v-col cols="6">
                <v-text-field v-model.number="form.amount" label="Menge *" type="number" min="0.01" step="0.1" />
              </v-col>
              <v-col cols="6">
                <v-select v-model="form.unit" label="Einheit *" :items="unitOptions" />
              </v-col>
            </v-row>
            <v-text-field v-model="form.harvest_date" label="Datum *" type="date" class="mb-2" />
            <v-rating v-model="form.quality_rating" label="Qualität" hover length="5" class="mb-4" />
            <v-textarea v-model="form.notes" label="Notizen" rows="2" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!form.amount || !form.harvest_date" @click="saveHarvest">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

