<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const router = useRouter();

const username = ref("");
const password = ref("");
const showPassword = ref(false);

async function handleLogin() {
  const success = await auth.login(username.value, password.value);
  if (success) {
    router.push({ name: "dashboard" });
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
            <v-form @submit.prevent="handleLogin">
              <v-text-field
                v-model="username"
                label="Benutzername"
                prepend-inner-icon="mdi-account"
                autocomplete="username"
                :disabled="auth.loading"
                class="mb-2"
              />

              <v-text-field
                v-model="password"
                label="Passwort"
                prepend-inner-icon="mdi-lock"
                :type="showPassword ? 'text' : 'password'"
                :append-inner-icon="showPassword ? 'mdi-eye-off' : 'mdi-eye'"
                autocomplete="current-password"
                :disabled="auth.loading"
                class="mb-4"
                @click:append-inner="showPassword = !showPassword"
              />

              <v-alert
                v-if="auth.error"
                type="error"
                variant="tonal"
                class="mb-4"
                closable
                @click:close="auth.error = null"
              >
                {{ auth.error }}
              </v-alert>

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="auth.loading"
                :disabled="!username || !password"
              >
                <v-icon start icon="mdi-login" />
                Anmelden
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

