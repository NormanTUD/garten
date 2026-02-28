<script setup lang="ts">
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();
</script>

<template>
  <v-bottom-navigation grow color="primary" class="d-md-none">
    <v-btn to="/" value="dashboard">
      <v-icon>mdi-view-dashboard</v-icon>
      <span>Home</span>
    </v-btn>

    <v-btn to="/garden" value="garden">
      <v-icon>mdi-flower</v-icon>
      <span>Garten</span>
    </v-btn>

    <v-btn to="/finance" value="finance">
      <v-icon>mdi-cash-register</v-icon>
      <span>Finanzen</span>
    </v-btn>

    <v-btn to="/duty" value="duty">
      <v-icon>mdi-shovel</v-icon>
      <span>Stunden</span>
    </v-btn>

    <!--
    <v-btn to="/harvest" value="harvest">
      <v-icon>mdi-basket</v-icon>
      <span>Ernte</span>
    </v-btn>
    -->

    <v-btn v-if="auth.isAdmin" to="/admin" value="admin">
      <v-icon>mdi-cog</v-icon>
      <span>Admin</span>
    </v-btn>
  </v-bottom-navigation>
</template>

