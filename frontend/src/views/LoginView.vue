<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";

// Login-Felder
const email = ref("");
const password = ref("");

// PWA-Installationslogik
const deferredPrompt = ref<any>(null);
const showInstallBtn = ref(false);

function onBeforeInstallPrompt(e: Event) {
  e.preventDefault();
  deferredPrompt.value = e;
  showInstallBtn.value = true;
}

async function installPwa() {
  if (!deferredPrompt.value) return;
  deferredPrompt.value.prompt();
  const { outcome } = await deferredPrompt.value.userChoice;
  if (outcome === "accepted") {
    showInstallBtn.value = false;
  }
  deferredPrompt.value = null;
}

onMounted(() => {
  window.addEventListener("beforeinstallprompt", onBeforeInstallPrompt);
});

onUnmounted(() => {
  window.removeEventListener("beforeinstallprompt", onBeforeInstallPrompt);
});

// Login-Handler
function handleLogin() {
  console.log("Login attempted with:", email.value, password.value);
  // Hier kannst du die Login-Logik hinzufügen
}
</script>

<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="5" lg="4">
        <v-card class="pa-4">
          <v-card-title class="text-center pb-6">
            <v-icon icon="mdi-sprout" size="64" color="primary" />
            <div class="text-h4 mt-2 font-weight-bold text-primary">
              GartenApp
            </div>
            <div class="text-subtitle-1 text-medium-emphasis">
              Schrebergarten-Management
            </div>
          </v-card-title>

          <v-card-text>
            <!-- Login-Formular -->
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="email"
                label="E-Mail"
                type="email"
                required
                outlined
                dense
              />
              <v-text-field
                v-model="password"
                label="Passwort"
                type="password"
                required
                outlined
                dense
              />
              <v-btn type="submit" color="primary" block>
                Login
              </v-btn>
            </v-form>
          </v-card-text>

          <!-- PWA Install Button -->
          <v-btn
            v-if="showInstallBtn"
            color="primary"
            block
            class="mt-4"
            @click="installPwa"
          >
            <v-icon start icon="mdi-download" />
            App installieren
          </v-btn>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

