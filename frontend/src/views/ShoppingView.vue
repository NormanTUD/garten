<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface ShoppingItem {
  id: number;
  title: string;
  notes: string | null;
  quantity: string | null;
  category: string | null;
  is_recurring: boolean;
  added_by_name: string;
  added_by_id: number;
  created_at: string;
  purchased: boolean;
  purchased_by_name: string | null;
  purchased_at: string | null;
  cost_cents: number | null;
  expense_id: number | null;
}

const items = ref<ShoppingItem[]>([]);
const loading = ref(true);
const showPurchased = ref(false);

// ─── Add Dialog ───────────────────────────────────────────
const showAddDialog = ref(false);
const addForm = ref({
  title: "",
  quantity: "",
  category: "",
  notes: "",
  is_recurring: false,
});

const categories = [
  "Erde & Substrate",
  "Samen & Pflanzen",
  "Dünger",
  "Werkzeug",
  "Bewässerung",
  "Baumaterial",
  "Schädlingsbekämpfung",
  "Lebensmittel",
  "Sonstiges",
];

// ─── Purchase Dialog ──────────────────────────────────────
const showPurchaseDialog = ref(false);
const purchaseItem = ref<ShoppingItem | null>(null);
const purchaseForm = ref({
  cost_euros: "",
  notes: "",
});

// ─── Computed ─────────────────────────────────────────────
const recurringItems = computed(() => items.value.filter((i) => i.is_recurring));
const openItems = computed(() => items.value.filter((i) => !i.purchased && !i.is_recurring));
const purchasedItems = computed(() => items.value.filter((i) => i.purchased && !i.is_recurring));

const groupedOpenItems = computed(() => {
  const groups: Record<string, ShoppingItem[]> = {};
  for (const item of openItems.value) {
    const cat = item.category || "Sonstiges";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(item);
  }
  return Object.entries(groups).sort(([a], [b]) => a.localeCompare(b));
});

const totalSpent = computed(() => {
  return items.value
    .filter((i) => i.purchased)
    .reduce((sum, i) => sum + (i.cost_cents || 0), 0);
});

// ─── Helpers ──────────────────────────────────────────────
function eur(cents: number): string {
  return (cents / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" });
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "gerade eben";
  if (hours < 24) return `vor ${hours}h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "gestern";
  return `vor ${days} Tagen`;
}

// ─── API ──────────────────────────────────────────────────
async function fetchItems() {
  loading.value = true;
  try {
    items.value = await api.get<ShoppingItem[]>("/shopping/", {
      include_purchased: showPurchased.value || true,  // Immer alle laden für recurring
    });
  } catch (e) {
    console.error("Failed to fetch shopping items", e);
  } finally {
    loading.value = false;
  }
}

function openAddDialog(recurring = false) {
  addForm.value = { title: "", quantity: "", category: "", notes: "", is_recurring: recurring };
  showAddDialog.value = true;
}

async function submitAdd() {
  const payload: Record<string, unknown> = {
    title: addForm.value.title.trim(),
    is_recurring: addForm.value.is_recurring,
  };
  if (addForm.value.quantity.trim()) payload.quantity = addForm.value.quantity.trim();
  if (addForm.value.category) payload.category = addForm.value.category;
  if (addForm.value.notes.trim()) payload.notes = addForm.value.notes.trim();

  await api.post("/shopping/", payload);
  showAddDialog.value = false;
  await fetchItems();
}

function openPurchaseDialog(item: ShoppingItem) {
  purchaseItem.value = item;
  purchaseForm.value = { cost_euros: "", notes: "" };
  showPurchaseDialog.value = true;
}

async function submitPurchase() {
  if (!purchaseItem.value) return;
  const euros = parseFloat(purchaseForm.value.cost_euros.replace(",", "."));
  if (isNaN(euros) || euros <= 0) return;

  const payload: Record<string, unknown> = {
    cost_cents: Math.round(euros * 100),
  };
  if (purchaseForm.value.notes.trim()) {
    payload.notes = purchaseForm.value.notes.trim();
  }

  await api.post(`/shopping/${purchaseItem.value.id}/purchase`, payload);
  showPurchaseDialog.value = false;
  await fetchItems();
}

async function resetRecurringItem(id: number) {
  await api.post(`/shopping/${id}/reset`);
  await fetchItems();
}

async function unpurchaseItem(id: number) {
  if (!confirm("Kauf rückgängig machen? Die Finanzbuchung wird gelöscht.")) return;
  await api.post(`/shopping/${id}/unpurchase`);
  await fetchItems();
}

async function toggleRecurring(item: ShoppingItem) {
  await api.put(`/shopping/${item.id}`, { is_recurring: !item.is_recurring });
  await fetchItems();
}

async function deleteItem(id: number) {
  if (!confirm("Eintrag wirklich löschen?")) return;
  await api.delete(`/shopping/${id}`);
  await fetchItems();
}

onMounted(fetchItems);
</script>

<template>
  <div>
    <!-- Header -->
    <div class="d-flex align-center mb-4 flex-wrap ga-2">
      <h1 class="text-h4">
        <v-icon icon="mdi-cart" class="mr-2" />Einkaufsliste
      </h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openAddDialog(false)">
        Hinzufügen
      </v-btn>
    </div>

    <!-- Summary -->
    <v-row dense class="mb-4">
      <v-col cols="4">
        <v-card variant="tonal" color="primary">
          <v-card-text class="text-center pa-3">
            <div class="text-h4 font-weight-bold">{{ openItems.length }}</div>
            <div class="text-caption">Offen</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card variant="tonal" color="info">
          <v-card-text class="text-center pa-3">
            <div class="text-h4 font-weight-bold">{{ recurringItems.length }}</div>
            <div class="text-caption">Dauerhaft</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="4">
        <v-card variant="tonal" color="success">
          <v-card-text class="text-center pa-3">
            <div class="text-h4 font-weight-bold">{{ eur(totalSpent) }}</div>
            <div class="text-caption">Ausgegeben</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-skeleton-loader v-if="loading" type="list-item@5" />

    <template v-else>
      <!-- ═══ Recurring Items (Dauerhaft) ═══ -->
      <template v-if="recurringItems.length > 0">
        <div class="text-subtitle-2 font-weight-bold text-medium-emphasis mt-4 mb-2">
          <v-icon icon="mdi-repeat" size="small" class="mr-1" />
          Immer mitbringen ({{ recurringItems.length }})
        </div>

        <v-card variant="outlined" class="mb-4">
          <v-list density="compact">
            <v-list-item v-for="item in recurringItems" :key="item.id">
              <template #prepend>
                <v-btn
                  v-if="!item.purchased"
                  icon
                  variant="text"
                  color="success"
                  size="small"
                  @click="openPurchaseDialog(item)"
                >
                  <v-icon icon="mdi-checkbox-blank-circle-outline" />
                </v-btn>
                <v-btn
                  v-else
                  icon
                  variant="text"
                  color="success"
                  size="small"
                  @click="resetRecurringItem(item.id)"
                >
                  <v-icon icon="mdi-checkbox-marked-circle" />
                </v-btn>
              </template>

              <template #title>
                <span :class="item.purchased ? 'text-decoration-line-through text-medium-emphasis' : 'font-weight-bold'">
                  {{ item.title }}
                </span>
                <v-chip size="x-small" color="info" variant="flat" class="ml-2">
                  <v-icon start icon="mdi-repeat" size="x-small" />dauerhaft
                </v-chip>
                <v-chip v-if="item.quantity" size="x-small" variant="tonal" class="ml-1">
                  {{ item.quantity }}
                </v-chip>
                <v-chip v-if="item.purchased && item.cost_cents" size="x-small" color="success" variant="flat" class="ml-1">
                  {{ eur(item.cost_cents) }}
                </v-chip>
              </template>

              <template #subtitle>
                <template v-if="item.purchased">
                  ✓ {{ item.purchased_by_name }} · {{ timeAgo(item.purchased_at!) }}
                  <span class="text-caption text-success ml-1">– klick ○ zum Zurücksetzen</span>
                </template>
                <template v-else>
                  {{ item.added_by_name }}
                  <template v-if="item.notes"> · {{ item.notes }}</template>
                </template>
              </template>

              <template #append>
                <v-btn
                  size="x-small"
                  icon="mdi-repeat-off"
                  variant="text"
                  color="grey"
                  title="Nicht mehr dauerhaft"
                  @click="toggleRecurring(item)"
                />
                <v-btn
                  size="x-small"
                  icon="mdi-delete"
                  variant="text"
                  color="error"
                  @click="deleteItem(item.id)"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card>

        <v-btn
          variant="text"
          color="info"
          size="small"
          prepend-icon="mdi-plus"
          class="mb-4"
          @click="openAddDialog(true)"
        >
          Dauerhaften Artikel hinzufügen
        </v-btn>
      </template>

      <!-- ═══ Open Items (grouped by category) ═══ -->
      <div v-if="openItems.length === 0 && recurringItems.length === 0" class="text-center py-8">
        <v-icon icon="mdi-cart-check" size="64" color="success" />
        <p class="text-body-1 text-grey mt-2">Alles eingekauft! 🎉</p>
      </div>

      <template v-for="[category, catItems] in groupedOpenItems" :key="category">
        <div class="text-subtitle-2 font-weight-bold text-medium-emphasis mt-4 mb-2">
          {{ category }} ({{ catItems.length }})
        </div>

        <v-card variant="outlined" class="mb-2">
          <v-list density="compact">
            <v-list-item v-for="item in catItems" :key="item.id">
              <template #prepend>
                <v-btn
                  icon
                  variant="text"
                  color="success"
                  size="small"
                  @click="openPurchaseDialog(item)"
                >
                  <v-icon icon="mdi-checkbox-blank-circle-outline" />
                </v-btn>
              </template>

              <template #title>
                <span class="font-weight-bold">{{ item.title }}</span>
                <v-chip v-if="item.quantity" size="x-small" variant="tonal" class="ml-2">
                  {{ item.quantity }}
                </v-chip>
              </template>

              <template #subtitle>
                {{ item.added_by_name }} · {{ timeAgo(item.created_at) }}
                <template v-if="item.notes"> · {{ item.notes }}</template>
              </template>

              <template #append>
                <v-btn
                  size="x-small"
                  icon="mdi-repeat"
                  variant="text"
                  color="info"
                  title="Dauerhaft machen"
                  @click="toggleRecurring(item)"
                />
                <v-btn
                  size="x-small"
                  icon="mdi-delete"
                  variant="text"
                  color="error"
                  @click="deleteItem(item.id)"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </template>

      <!-- ═══ Purchased Items ═══ -->
      <v-divider class="my-6" />

      <v-switch
        v-model="showPurchased"
        label="Erledigte anzeigen"
        density="compact"
        hide-details
        color="primary"
        class="mb-4"
        @update:model-value="fetchItems"
      />

      <template v-if="showPurchased && purchasedItems.length > 0">
        <v-card variant="outlined">
          <v-list density="compact">
            <v-list-item v-for="item in purchasedItems" :key="item.id">
              <template #prepend>
                <v-avatar color="success" variant="tonal" size="32">
                  <v-icon icon="mdi-check" size="small" />
                </v-avatar>
              </template>

              <template #title>
                <span class="text-decoration-line-through text-medium-emphasis">
                  {{ item.title }}
                </span>
                <v-chip v-if="item.cost_cents" size="x-small" color="success" variant="flat" class="ml-2">
                  {{ eur(item.cost_cents) }}
                </v-chip>
              </template>

              <template #subtitle>
                Gekauft von {{ item.purchased_by_name }}
                <template v-if="item.purchased_at">
                  · {{ new Date(item.purchased_at).toLocaleDateString("de-DE") }}
                </template>
                <v-chip v-if="item.expense_id" size="x-small" variant="tonal" color="info" class="ml-1">
                  📊 verbucht
                </v-chip>
              </template>

              <template #append>
                <v-btn
                  v-if="auth.isAdmin"
                  size="x-small"
                  icon="mdi-undo"
                  variant="text"
                  color="warning"
                  @click="unpurchaseItem(item.id)"
                />
              </template>
            </v-list-item>
          </v-list>
        </v-card>
      </template>
    </template>

    <!-- ═══ Add Dialog ═══ -->
    <v-dialog v-model="showAddDialog" max-width="500">
      <v-card>
        <v-card-title>Artikel hinzufügen</v-card-title>
        <v-card-text>
          <v-text-field
            v-model="addForm.title"
            label="Was wird gebraucht?"
            placeholder="z.B. Blumenerde, Tomatensamen..."
            autofocus
            class="mb-3"
          />
          <v-text-field
            v-model="addForm.quantity"
            label="Menge (optional)"
            placeholder="z.B. 3 Säcke, 10kg"
            class="mb-3"
          />
          <v-select
            v-model="addForm.category"
            :items="categories"
            label="Kategorie (optional)"
            clearable
            class="mb-3"
          />
          <v-textarea
            v-model="addForm.notes"
            label="Notizen (optional)"
            rows="2"
            class="mb-3"
          />
          <v-checkbox
            v-model="addForm.is_recurring"
            label="Dauerhaft auf der Liste (z.B. Kaffee, Müllbeutel)"
            hint="Wird nach dem Kauf nicht entfernt, sondern kann erneut abgehakt werden"
            persistent-hint
            color="info"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showAddDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :disabled="!addForm.title.trim()"
            @click="submitAdd"
          >
            Hinzufügen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Purchase Dialog ═══ -->
    <v-dialog v-model="showPurchaseDialog" max-width="500">
      <v-card v-if="purchaseItem">
        <v-card-title>
          <v-icon icon="mdi-cart-check" class="mr-2" />
          Gekauft: {{ purchaseItem.title }}
        </v-card-title>
        <v-card-text>
          <div v-if="purchaseItem.quantity" class="text-body-2 mb-3">
            Menge: <strong>{{ purchaseItem.quantity }}</strong>
          </div>

          <v-text-field
            v-model="purchaseForm.cost_euros"
            label="Preis (€)"
            placeholder="z.B. 12,50"
            type="text"
            inputmode="decimal"
            prefix="€"
            autofocus
            hint="Der Betrag wird dir gutgeschrieben und als Gartenausgabe verbucht"
            persistent-hint
            class="mb-3"
          />
          <v-textarea
            v-model="purchaseForm.notes"
            label="Notiz (optional)"
            rows="2"
            placeholder="z.B. Baumarkt Hornbach"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="showPurchaseDialog = false">Abbrechen</v-btn>
          <v-btn
            color="success"
            :disabled="!purchaseForm.cost_euros || parseFloat(purchaseForm.cost_euros.replace(',', '.')) <= 0"
            @click="submitPurchase"
          >
            <v-icon start icon="mdi-check" />
            Als gekauft markieren
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

