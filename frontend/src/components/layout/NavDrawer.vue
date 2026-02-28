<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "@/stores/auth";
import { useDisplay } from "vuetify";

const auth = useAuthStore();
const rail = ref(false);
const { mdAndUp } = useDisplay();

const navItems = [
/*
  { title: "Dashboard", icon: "mdi-view-dashboard", to: "/" },
  { title: "Garten & Beete", icon: "mdi-flower", to: "/garden" },
  { title: "Ernte", icon: "mdi-basket", to: "/harvest" },
  { title: "Bewässerung", icon: "mdi-water", to: "/watering" },
  */
  { title: "Finanzen", icon: "mdi-cash-register", to: "/finance" },
  { title: "Gartenstunden", icon: "mdi-shovel", to: "/duty" },  // NEU
  { title: "Nachrichten", icon: "mdi-email", to: "/messages" },
];

const adminItems = [
  { title: "Administration", icon: "mdi-cog", to: "/admin" },
];
</script>

<template>
  <v-navigation-drawer
    v-if="mdAndUp"
    :rail="rail"
    permanent
    @click="rail = false"
  >
    <v-list density="compact" nav>
      <v-list-item
        v-for="item in navItems"
        :key="item.to"
        :prepend-icon="item.icon"
        :title="item.title"
        :to="item.to"
        rounded="lg"
      />
    </v-list>

    <v-divider v-if="auth.isAdmin" class="my-2" />

    <v-list v-if="auth.isAdmin" density="compact" nav>
      <v-list-item
        v-for="item in adminItems"
        :key="item.to"
        :prepend-icon="item.icon"
        :title="item.title"
        :to="item.to"
        rounded="lg"
      />
    </v-list>

    <template #append>
      <div class="pa-2 d-flex justify-center">
        <v-btn
          :icon="rail ? 'mdi-chevron-right' : 'mdi-chevron-left'"
          variant="text"
          size="small"
          @click.stop="rail = !rail"
        />
      </div>
    </template>
  </v-navigation-drawer>
</template>
