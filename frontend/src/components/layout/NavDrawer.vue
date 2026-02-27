<script setup lang="ts">
import { ref } from "vue";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
const rail = ref(false);

const navItems = [
  { title: "Dashboard", icon: "mdi-view-dashboard", to: "/" },
  { title: "Garten & Beete", icon: "mdi-flower", to: "/garden" },
  { title: "Ernte", icon: "mdi-basket", to: "/harvest" },
  { title: "Bewässerung", icon: "mdi-water", to: "/watering" },
];

const adminItems = [
  { title: "Administration", icon: "mdi-cog", to: "/admin" },
];
</script>

<template>
  <v-navigation-drawer
    :rail="rail"
    permanent
    class="d-none d-md-block"
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

