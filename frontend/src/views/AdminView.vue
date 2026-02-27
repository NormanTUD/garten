<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";

interface User {
  id: number;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

const users = ref<User[]>([]);
const loading = ref(true);
const showDialog = ref(false);

const form = ref({
  username: "",
  password: "",
  display_name: "",
  role: "user",
});

onMounted(() => loadUsers());

async function loadUsers() {
  loading.value = true;
  try {
    users.value = await api.get<User[]>("/users/");
  } finally {
    loading.value = false;
  }
}

function openDialog() {
  form.value = { username: "", password: "", display_name: "", role: "user" };
  showDialog.value = true;
}

async function createUser() {
  await api.post("/users/", form.value);
  showDialog.value = false;
  await loadUsers();
}

async function toggleActive(user: User) {
  await api.patch(`/users/${user.id}`, { is_active: !user.is_active });
  await loadUsers();
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4">Administration</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-account-plus" @click="openDialog">
        Neuer Benutzer
      </v-btn>
    </div>

    <v-card>
      <v-card-title>Benutzer</v-card-title>
      <v-skeleton-loader v-if="loading" type="table" />
      <v-table v-else>
        <thead>
          <tr>
            <th>Benutzername</th>
            <th>Anzeigename</th>
            <th>Rolle</th>
            <th>Status</th>
            <th>Erstellt</th>
            <th>Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>{{ user.username }}</td>
            <td>{{ user.display_name }}</td>
            <td>
              <v-chip :color="user.role === 'admin' ? 'primary' : 'default'" size="small">
                {{ user.role === 'admin' ? 'Admin' : 'Benutzer' }}
              </v-chip>
            </td>
            <td>
              <v-chip :color="user.is_active ? 'success' : 'error'" size="small">
                {{ user.is_active ? 'Aktiv' : 'Inaktiv' }}
              </v-chip>
            </td>
            <td>{{ new Date(user.created_at).toLocaleDateString('de-DE') }}</td>
            <td>
              <v-btn
                size="small"
                :color="user.is_active ? 'error' : 'success'"
                variant="text"
                @click="toggleActive(user)"
              >
                {{ user.is_active ? 'Deaktivieren' : 'Aktivieren' }}
              </v-btn>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Create User Dialog -->
    <v-dialog v-model="showDialog" max-width="500">
      <v-card>
        <v-card-title>Neuer Benutzer</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="createUser">
            <v-text-field v-model="form.username" label="Benutzername *" class="mb-2" />
            <v-text-field v-model="form.password" label="Passwort *" type="password" class="mb-2" />
            <v-text-field v-model="form.display_name" label="Anzeigename *" class="mb-2" />
            <v-select v-model="form.role" label="Rolle" :items="[{ title: 'Benutzer', value: 'user' }, { title: 'Admin', value: 'admin' }]" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!form.username || !form.password || !form.display_name" @click="createUser">Erstellen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

