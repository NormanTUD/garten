<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth";
import AppBar from "@/components/layout/AppBar.vue";
import NavDrawer from "@/components/layout/NavDrawer.vue";
import BottomNav from "@/components/layout/BottomNav.vue";

const route = useRoute();
const auth = useAuthStore();

const showLayout = computed(() => auth.isAuthenticated && route.name !== "login");
</script>

<template>
  <v-app>
    <template v-if="showLayout">
      <AppBar />
      <NavDrawer />
    </template>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <template v-if="showLayout">
      <BottomNav />
    </template>
  </v-app>
</template>

