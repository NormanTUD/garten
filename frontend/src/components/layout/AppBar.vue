<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useRouter } from "vue-router";
import { api } from "@/api/client";

const auth = useAuthStore();
const router = useRouter();
const unreadCount = ref(0);
let pollInterval: ReturnType<typeof setInterval> | null = null;

const emit = defineEmits<{
  (e: "toggle-drawer"): void;
}>();

async function fetchUnread() {
  try {
    const data = await api.get<{ count: number }>("/messages/unread-count");
    unreadCount.value = data.count;
  } catch {
    // silently fail
  }
}

onMounted(() => {
  fetchUnread();
  pollInterval = setInterval(fetchUnread, 30000); // poll every 30s
});

async function handleLogout() {
  if (pollInterval) clearInterval(pollInterval);
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

    <v-btn icon @click="router.push('/messages')" class="mr-1">
      <v-badge
        v-if="unreadCount > 0"
        :content="unreadCount"
        color="error"
        floating
      >
        <v-icon icon="mdi-bell" />
      </v-badge>
      <v-icon v-else icon="mdi-bell-outline" />
      <v-tooltip activator="parent" location="bottom">Nachrichten</v-tooltip>
    </v-btn>

    <v-chip variant="text" class="mr-2 d-none d-sm-flex">
      <v-icon start icon="mdi-account" />
      {{ auth.displayName }}
    </v-chip>

    <v-btn icon="mdi-logout" @click="handleLogout" />
  </v-app-bar>
</template>

