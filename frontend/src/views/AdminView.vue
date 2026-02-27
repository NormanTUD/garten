<script setup lang="ts">
import { ref, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

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

// Create user
const showCreateDialog = ref(false);
const createForm = ref({
  username: "",
  password: "",
  display_name: "",
  role: "user",
});
const createError = ref("");

// Edit user
const showEditDialog = ref(false);
const editForm = ref({
  id: 0,
  display_name: "",
  role: "user",
  password: "",
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

function openCreateDialog() {
  createForm.value = { username: "", password: "", display_name: "", role: "user" };
  createError.value = "";
  showCreateDialog.value = true;
}

async function createUser() {
  createError.value = "";
  if (!createForm.value.username || !createForm.value.password || !createForm.value.display_name) {
    createError.value = "Alle Felder ausfüllen";
    return;
  }
  if (createForm.value.password.length < 6) {
    createError.value = "Passwort muss mindestens 6 Zeichen haben";
    return;
  }
  try {
    await api.post("/users/", createForm.value);
    showCreateDialog.value = false;
    await loadUsers();
  } catch (e: any) {
    createError.value = e?.message || "Fehler beim Erstellen";
  }
}

function openEditDialog(user: User) {
  editForm.value = {
    id: user.id,
    display_name: user.display_name,
    role: user.role,
    password: "",
  };
  showEditDialog.value = true;
}

async function saveEdit() {
  const data: any = {
    display_name: editForm.value.display_name,
    role: editForm.value.role,
  };
  if (editForm.value.password) data.password = editForm.value.password;
  try {
    await api.patch(`/users/${editForm.value.id}`, data);
    showEditDialog.value = false;
    await loadUsers();
  } catch (e: any) {
    alert(e?.message || "Fehler beim Speichern");
  }
}

async function toggleActive(user: User) {
  const newState = !user.is_active;
  try {
    await api.patch(`/users/${user.id}`, { is_active: newState });
    await loadUsers();
  } catch (e: any) {
    alert(e?.message || "Fehler");
  }
}

function canDeactivate(user: User): boolean {
  // Cannot deactivate yourself
  if (user.id === auth.user?.id) return false;
  // Cannot deactivate admins
  if (user.role === "admin") return false;
  return true;
}

function canReactivate(user: User): boolean {
  return !user.is_active;
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4">
      <h1 class="text-h4">Administration</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-account-plus" @click="openCreateDialog">
        Neuer Benutzer
      </v-btn>
    </div>

    <v-skeleton-loader v-if="loading" type="table" />

    <v-card v-else>
      <v-table>
        <thead>
          <tr>
            <th>Benutzer</th>
            <th>Anzeigename</th>
            <th>Rolle</th>
            <th>Status</th>
            <th>Erstellt</th>
            <th class="text-right">Aktionen</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id" :class="!user.is_active ? 'text-medium-emphasis' : ''">
            <td>
              <v-icon v-if="user.role === 'admin'" icon="mdi-shield-account" color="primary" size="small" class="mr-1" />
              {{ user.username }}
              <v-chip v-if="user.id === auth.user?.id" size="x-small" color="info" variant="flat" class="ml-1">du</v-chip>
            </td>
            <td>{{ user.display_name }}</td>
            <td>
              <v-chip :color="user.role === 'admin' ? 'primary' : 'default'" size="small" variant="tonal">
                {{ user.role === 'admin' ? '👑 Admin' : '👤 User' }}
              </v-chip>
            </td>
            <td>
              <v-chip :color="user.is_active ? 'success' : 'error'" size="small" variant="flat">
                {{ user.is_active ? 'Aktiv' : 'Deaktiviert' }}
              </v-chip>
            </td>
            <td>{{ new Date(user.created_at).toLocaleDateString('de-DE') }}</td>
            <td class="text-right">
              <v-btn size="small" icon="mdi-pencil" variant="text" @click="openEditDialog(user)" />
              <v-btn
                v-if="user.is_active && canDeactivate(user)"
                size="small"
                icon="mdi-account-off"
                variant="text"
                color="error"
                @click="toggleActive(user)"
              >
                <v-icon icon="mdi-account-off" />
                <v-tooltip activator="parent" location="top">Deaktivieren</v-tooltip>
              </v-btn>
              <v-btn
                v-if="canReactivate(user)"
                size="small"
                icon="mdi-account-check"
                variant="text"
                color="success"
                @click="toggleActive(user)"
              >
                <v-icon icon="mdi-account-check" />
                <v-tooltip activator="parent" location="top">Reaktivieren</v-tooltip>
              </v-btn>
              <v-chip
                v-if="user.is_active && !canDeactivate(user)"
                size="x-small"
                variant="tonal"
                class="ml-1"
              >
                {{ user.id === auth.user?.id ? 'Eigenes Konto' : 'Admin geschützt' }}
              </v-chip>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- ═══ Create User Dialog ═════════════════════════════════ -->
    <v-dialog v-model="showCreateDialog" max-width="500">
      <v-card>
        <v-card-title>Neuen Benutzer anlegen</v-card-title>
        <v-card-text>
          <v-alert v-if="createError" type="error" variant="tonal" density="compact" class="mb-3">
            {{ createError }}
          </v-alert>
          <v-form @submit.prevent="createUser">
            <v-text-field
              v-model="createForm.username"
              label="Benutzername *"
              placeholder="z.B. maria"
              autofocus
              variant="outlined"
              density="comfortable"
              class="mb-3"
              hint="Mindestens 3 Zeichen"
              persistent-hint
            />
            <v-text-field
              v-model="createForm.display_name"
              label="Anzeigename *"
              placeholder="z.B. Maria Müller"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />
            <v-text-field
              v-model="createForm.password"
              label="Passwort *"
              type="password"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              hint="Mindestens 6 Zeichen"
              persistent-hint
            />
            <v-btn-toggle
              v-model="createForm.role"
              mandatory
              color="primary"
              density="comfortable"
            >
              <v-btn value="user">👤 User</v-btn>
              <v-btn value="admin">👑 Admin</v-btn>
            </v-btn-toggle>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCreateDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :disabled="!createForm.username || !createForm.password || !createForm.display_name"
            @click="createUser"
          >
            Anlegen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Edit User Dialog ═══════════════════════════════════ -->
    <v-dialog v-model="showEditDialog" max-width="500">
      <v-card>
        <v-card-title>Benutzer bearbeiten</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEdit">
            <v-text-field
              v-model="editForm.display_name"
              label="Anzeigename *"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />
            <v-text-field
              v-model="editForm.password"
              label="Neues Passwort"
              type="password"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              hint="Leer lassen = nicht ändern"
              persistent-hint
            />
            <v-btn-toggle
              v-model="editForm.role"
              mandatory
              color="primary"
              density="comfortable"
            >
              <v-btn value="user">👤 User</v-btn>
              <v-btn value="admin">👑 Admin</v-btn>
            </v-btn-toggle>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showEditDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!editForm.display_name" @click="saveEdit">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
