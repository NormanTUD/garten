<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface Stats {
  gardens: number;
  beds: number;
  plants: number;
  harvests: number;
}

const stats = ref<Stats>({ gardens: 0, beds: 0, plants: 0, harvests: 0 });
const loading = ref(true);

onMounted(async () => {
  try {
    const [gardens, plants, harvests] = await Promise.all([
      api.get<any[]>("/gardens/"),
      api.get<any[]>("/plants/"),
      api.get<any[]>("/harvests/"),
    ]);

    stats.value.gardens = gardens.length;
    stats.value.plants = plants.length;
    stats.value.harvests = harvests.length;

    // Count beds across all gardens
    let bedCount = 0;
    for (const garden of gardens) {
      const beds = await api.get<any[]>("/beds/", { garden_id: garden.id });
      bedCount += beds.length;
    }
    stats.value.beds = bedCount;
  } catch {
    // Silently fail, show zeros
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div>
    <h1 class="text-h4 mb-6">
      Hallo, {{ auth.displayName }}! 👋
    </h1>

    <v-row>
      <v-col cols="6" md="3">
        <v-card color="primary" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-flower" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.gardens }}</div>
            <div class="text-body-2">Gärten</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="6" md="3">
        <v-card color="secondary" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-grid" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.beds }}</div>
            <div class="text-body-2">Beete</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="6" md="3">
        <v-card color="accent" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-leaf" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.plants }}</div>
            <div class="text-body-2">Pflanzen</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="6" md="3">
        <v-card color="success" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-basket" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.harvests }}</div>
            <div class="text-body-2">Ernten</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-skeleton-loader v-if="loading" type="card" class="mt-6" />
  </div>
</template>

