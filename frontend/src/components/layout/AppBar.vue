<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";
import { useRouter } from "vue-router";

const auth = useAuthStore();
const router = useRouter();

const emit = defineEmits<{
  (e: "toggle-drawer"): void;
}>();

async function handleLogout() {
  await auth.logout();
  router.push({ name: "login" });
}
</script>

<template>
  <v-app-bar color="primary" density="comfortable">
    <v-app-bar-nav-icon
      class="d-none d-md-flex"
      @click="emit('toggle-drawer')"
    />

    <v-app-bar-title>
      <v-icon icon="mdi-sprout" />
      <span class="d-none d-sm-inline ml-2">GartenApp</span>
    </v-app-bar-title>

    <v-spacer />

    <v-chip variant="text" class="mr-2 d-none d-sm-flex">
      <v-icon start icon="mdi-account" />
      {{ auth.displayName }}
    </v-chip>

    <v-btn icon="mdi-logout" @click="handleLogout" />
  </v-app-bar>
</template>

