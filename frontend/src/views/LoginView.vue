<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = useRouter();
const auth = useAuthStore();

// Login-Felder
const username = ref("");
const password = ref("");
const showPassword = ref(false);

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
async function handleLogin() {
  const success = await auth.login(username.value, password.value);
  if (success) {
    router.push("/");
  }
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
            <!-- Error Banner -->
            <v-alert
              v-if="auth.error"
              type="error"
              variant="tonal"
              class="mb-4"
              closable
            >
              {{ auth.error }}
            </v-alert>

            <!-- Login-Formular -->
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Benutzername"
                prepend-inner-icon="mdi-account"
                required
                class="mb-2"
              />
              <v-text-field
                v-model="password"
                label="Passwort"
                :type="showPassword ? 'text' : 'password'"
                prepend-inner-icon="mdi-lock"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                @click:append-inner="showPassword = !showPassword"
                required
                class="mb-2"
              />
              <v-btn
                type="submit"
                color="primary"
                block
                size="large"
                :loading="auth.loading"
                :disabled="!username || !password"
              >
                <v-icon start icon="mdi-login" />
                Anmelden
              </v-btn>
            </v-form>
          </v-card-text>

          <!-- PWA Install Button -->
          <v-btn
            v-if="showInstallBtn"
            color="primary"
            variant="tonal"
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
