<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import AppBar from "@/components/layout/AppBar.vue";
import NavDrawer from "@/components/layout/NavDrawer.vue";
import BottomNav from "@/components/layout/BottomNav.vue";

const route = useRoute();
const auth = useAuthStore();
const drawerRail = ref(false);

const showLayout = computed(() => auth.isAuthenticated && route.name !== "login");
const isOffline = ref(false);
const showUpdateSnackbar = ref(false);

onMounted(() => {
  // Online/Offline detection
  isOffline.value = !navigator.onLine;
  window.addEventListener("online", () => (isOffline.value = false));
  window.addEventListener("offline", () => (isOffline.value = true));

  // PWA update detection
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.ready.then((registration) => {
      registration.addEventListener("updatefound", () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener("statechange", () => {
            if (newWorker.state === "activated") {
              showUpdateSnackbar.value = true;
            }
          });
        }
      });
    });
  }
});

function reloadApp() {
  window.location.reload();
}

function toggleDrawer() {                                         // NEU
  drawerRail.value = !drawerRail.value;
}
</script>

<template>
  <v-app>
    <!-- Offline Banner -->
    <v-banner
      v-if="isOffline"
      color="warning"
      icon="mdi-wifi-off"
      lines="one"
      density="compact"
      stacked
    >
      <template #text>
        Du bist offline. Einige Funktionen sind eingeschränkt.
      </template>
    </v-banner>

    <template v-if="showLayout">
      <AppBar @toggle-drawer="toggleDrawer" />
      <NavDrawer v-model:rail="drawerRail" />
    </template>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <template v-if="showLayout">
      <BottomNav />
    </template>

    <!-- PWA Update Snackbar -->
    <v-snackbar
      v-model="showUpdateSnackbar"
      color="primary"
      timeout="-1"
      location="bottom"
    >
      Eine neue Version ist verfügbar!
      <template #actions>
        <v-btn variant="text" @click="reloadApp">
          Aktualisieren
        </v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

