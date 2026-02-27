<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";

interface Garden {
  id: number;
  name: string;
  description: string | null;
  location_lat: number | null;
  location_lng: number | null;
  total_area_sqm: number | null;
}

interface Bed {
  id: number;
  garden_id: number;
  name: string;
  description: string | null;
  area_sqm: number | null;
  soil_type: string | null;
  sun_exposure: string | null;
}

const gardens = ref<Garden[]>([]);
const beds = ref<Record<number, Bed[]>>({});
const loading = ref(true);

// Garden form
const showGardenDialog = ref(false);
const gardenForm = ref({ name: "", description: "", location_lat: null as number | null, location_lng: null as number | null, total_area_sqm: null as number | null });

// Bed form
const showBedDialog = ref(false);
const bedForm = ref({ garden_id: 0, name: "", description: "", area_sqm: null as number | null, soil_type: "", sun_exposure: "" });

const sunOptions = [
  { title: "Volle Sonne", value: "full_sun" },
  { title: "Halbschatten", value: "partial_shade" },
  { title: "Schatten", value: "full_shade" },
];

onMounted(() => loadData());

async function loadData() {
  loading.value = true;
  try {
    gardens.value = await api.get<Garden[]>("/gardens/");
    for (const garden of gardens.value) {
      beds.value[garden.id] = await api.get<Bed[]>("/beds/", { garden_id: garden.id });
    }
  } finally {
    loading.value = false;
  }
}

async function saveGarden() {
  await api.post("/gardens/", gardenForm.value);
  showGardenDialog.value = false;
  gardenForm.value = { name: "", description: "", location_lat: null, location_lng: null, total_area_sqm: null };
  await loadData();
}

function openBedDialog(gardenId: number) {
  bedForm.value = { garden_id: gardenId, name: "", description: "", area_sqm: null, soil_type: "", sun_exposure: "" };
  showBedDialog.value = true;
}

async function saveBed() {
  const data: any = { ...bedForm.value };
  if (!data.soil_type) delete data.soil_type;
  if (!data.sun_exposure) delete data.sun_exposure;
  await api.post("/beds/", data);
  showBedDialog.value = false;
  await loadData();
}

async function deleteGarden(id: number) {
  await api.delete(`/gardens/${id}`);
  await loadData();
}

async function deleteBed(id: number) {
  await api.delete(`/beds/${id}`);
  await loadData();
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">Garten & Beete</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="showGardenDialog = true">
        Neuer Garten
      </v-btn>
    </div>

    <v-skeleton-loader v-if="loading" type="card@3" />

    <div v-else-if="gardens.length === 0" class="text-center py-12">
      <v-icon icon="mdi-flower-outline" size="80" color="grey" />
      <p class="text-h6 text-grey mt-4">Noch keine Gärten angelegt</p>
    </div>

    <v-expansion-panels v-else variant="accordion">
      <v-expansion-panel v-for="garden in gardens" :key="garden.id">
        <v-expansion-panel-title>
          <div class="d-flex align-center w-100">
            <v-icon icon="mdi-flower" color="primary" class="mr-3" />
            <div>
              <div class="font-weight-bold">{{ garden.name }}</div>
              <div v-if="garden.total_area_sqm" class="text-caption text-grey">
                {{ garden.total_area_sqm }} m²
              </div>
            </div>
            <v-spacer />
            <v-chip size="small" class="mr-2">
              {{ beds[garden.id]?.length || 0 }} Beete
            </v-chip>
          </div>
        </v-expansion-panel-title>

        <v-expansion-panel-text>
          <p v-if="garden.description" class="mb-4 text-body-2">{{ garden.description }}</p>

          <div class="d-flex mb-4">
            <v-btn size="small" color="primary" variant="tonal" prepend-icon="mdi-plus" @click="openBedDialog(garden.id)">
              Neues Beet
            </v-btn>
            <v-spacer />
            <v-btn size="small" color="error" variant="text" icon="mdi-delete" @click="deleteGarden(garden.id)" />
          </div>

          <v-row v-if="beds[garden.id]?.length">
            <v-col v-for="bed in beds[garden.id]" :key="bed.id" cols="12" sm="6" md="4">
              <v-card variant="outlined">
                <v-card-title class="d-flex align-center">
                  <v-icon icon="mdi-grid" class="mr-2" size="small" />
                  {{ bed.name }}
                  <v-spacer />
                  <v-btn size="x-small" color="error" variant="text" icon="mdi-delete" @click="deleteBed(bed.id)" />
                </v-card-title>
                <v-card-text>
                  <p v-if="bed.description" class="text-body-2 mb-2">{{ bed.description }}</p>
                  <v-chip v-if="bed.area_sqm" size="small" class="mr-1">{{ bed.area_sqm }} m²</v-chip>
                  <v-chip v-if="bed.soil_type" size="small" class="mr-1">{{ bed.soil_type }}</v-chip>
                  <v-chip v-if="bed.sun_exposure" size="small">
                    {{ bed.sun_exposure === 'full_sun' ? '☀️ Sonne' : bed.sun_exposure === 'partial_shade' ? '⛅ Halbschatten' : '🌑 Schatten' }}
                  </v-chip>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>

          <p v-else class="text-body-2 text-grey">Noch keine Beete in diesem Garten.</p>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <!-- Garden Dialog -->
    <v-dialog v-model="showGardenDialog" max-width="500">
      <v-card>
        <v-card-title>Neuer Garten</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveGarden">
            <v-text-field v-model="gardenForm.name" label="Name *" class="mb-2" />
            <v-textarea v-model="gardenForm.description" label="Beschreibung" rows="2" class="mb-2" />
            <v-row>
              <v-col cols="6">
                <v-text-field v-model.number="gardenForm.location_lat" label="Breitengrad" type="number" step="0.0001" />
              </v-col>
              <v-col cols="6">
                <v-text-field v-model.number="gardenForm.location_lng" label="Längengrad" type="number" step="0.0001" />
              </v-col>
            </v-row>
            <v-text-field v-model.number="gardenForm.total_area_sqm" label="Fläche (m²)" type="number" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showGardenDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!gardenForm.name" @click="saveGarden">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Bed Dialog -->
    <v-dialog v-model="showBedDialog" max-width="500">
      <v-card>
        <v-card-title>Neues Beet</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveBed">
            <v-text-field v-model="bedForm.name" label="Name *" class="mb-2" />
            <v-textarea v-model="bedForm.description" label="Beschreibung" rows="2" class="mb-2" />
            <v-text-field v-model.number="bedForm.area_sqm" label="Fläche (m²)" type="number" class="mb-2" />
            <v-text-field v-model="bedForm.soil_type" label="Bodenart" class="mb-2" />
            <v-select v-model="bedForm.sun_exposure" label="Sonneneinstrahlung" :items="sunOptions" clearable />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showBedDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!bedForm.name" @click="saveBed">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

