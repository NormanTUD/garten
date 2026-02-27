<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";
import PhotoCapture from "@/components/shared/PhotoCapture.vue";

const auth = useAuthStore();

// ─── Types ────────────────────────────────────────────────────────

interface Category {
  id: number;
  name: string;
  icon: string | null;
  is_active: boolean;
}

interface Split {
  id: number;
  user_id: number;
  user: { id: number; display_name: string };
  share_amount_cents: number;
  is_settled: boolean;
}

interface Expense {
  id: number;
  user: { id: number; display_name: string };
  category: { id: number; name: string; icon: string | null } | null;
  amount_cents: number;
  description: string;
  expense_date: string;
  receipt_image_path: string | null;
  notes: string | null;
  splits: Split[];
}

interface Payment {
  id: number;
  from_user: { id: number; display_name: string };
  to_user: { id: number; display_name: string };
  amount_cents: number;
  method: string;
  description: string | null;
  payment_date: string;
  confirmed_by_admin: boolean;
}

interface UserBalance {
  user_id: number;
  display_name: string;
  total_paid_cents: number;
  total_share_cents: number;
  balance_cents: number;
}

interface BalanceOverview {
  balances: UserBalance[];
  total_expenses_cents: number;
}

interface UserInfo {
  id: number;
  username: string;
  display_name: string;
}

// ─── State ────────────────────────────────────────────────────────

const tab = ref("expenses");
const loading = ref(true);

const categories = ref<Category[]>([]);
const expenses = ref<Expense[]>([]);
const payments = ref<Payment[]>([]);
const balance = ref<BalanceOverview | null>(null);
const users = ref<UserInfo[]>([]);

// Expense form
const showExpenseDialog = ref(false);
const expenseForm = ref({
  amount: null as number | null,
  description: "",
  category_id: null as number | null,
  expense_date: new Date().toISOString().split("T")[0],
  receipt_image_path: null as string | null,
  notes: "",
});

// Payment form
const showPaymentDialog = ref(false);
const paymentForm = ref({
  to_user_id: null as number | null,
  amount: null as number | null,
  method: "cash",
  description: "",
  payment_date: new Date().toISOString().split("T")[0],
});

// Category form
const showCategoryDialog = ref(false);
const categoryForm = ref({ name: "", icon: "" });

// ─── Computed ─────────────────────────────────────────────────────

const otherUsers = computed(() =>
  users.value.filter((u) => u.id !== auth.user?.id)
);

// ─── Load Data ────────────────────────────────────────────────────

onMounted(() => loadAll());

async function loadAll() {
  loading.value = true;
  try {
    const [cats, exps, pays, bal, usrs] = await Promise.all([
      api.get<Category[]>("/finance/categories/"),
      api.get<Expense[]>("/finance/expenses/"),
      api.get<Payment[]>("/finance/payments/"),
      api.get<BalanceOverview>("/finance/balance/"),
      auth.isAdmin ? api.get<UserInfo[]>("/users/") : Promise.resolve([]),
    ]);
    categories.value = cats;
    expenses.value = exps;
    payments.value = pays;
    balance.value = bal;
    if (usrs.length) users.value = usrs;
    else {
      // Non-admin: extract users from balance
      users.value = bal.balances.map((b) => ({
        id: b.user_id,
        username: "",
        display_name: b.display_name,
      }));
    }
  } finally {
    loading.value = false;
  }
}

// ─── Helpers ──────────────────────────────────────────────────────

function formatEuro(cents: number): string {
  return (cents / 100).toLocaleString("de-DE", {
    style: "currency",
    currency: "EUR",
  });
}

function balanceColor(cents: number): string {
  if (cents > 0) return "success";
  if (cents < 0) return "error";
  return "default";
}

function methodLabel(method: string): string {
  const map: Record<string, string> = {
    cash: "Bar",
    transfer: "Überweisung",
    material: "Sachleistung",
  };
  return map[method] || method;
}

// ─── Expense Actions ──────────────────────────────────────────────

function openExpenseDialog() {
  expenseForm.value = {
    amount: null,
    description: "",
    category_id: null,
    expense_date: new Date().toISOString().split("T")[0],
    receipt_image_path: null,
    notes: "",
  };
  showExpenseDialog.value = true;
}

async function saveExpense() {
  if (!expenseForm.value.amount) return;
  const data: any = {
    amount_cents: Math.round(expenseForm.value.amount * 100),
    description: expenseForm.value.description,
    expense_date: expenseForm.value.expense_date,
  };
  if (expenseForm.value.category_id) data.category_id = expenseForm.value.category_id;
  if (expenseForm.value.receipt_image_path) data.receipt_image_path = expenseForm.value.receipt_image_path;
  if (expenseForm.value.notes) data.notes = expenseForm.value.notes;

  await api.post("/finance/expenses/", data);
  showExpenseDialog.value = false;
  await loadAll();
}

async function deleteExpense(id: number) {
  await api.delete(`/finance/expenses/${id}`);
  await loadAll();
}

async function toggleSettle(expense: Expense, split: Split) {
  if (split.is_settled) {
    await api.patch(`/finance/expenses/${expense.id}/splits/${split.id}/unsettle`);
  } else {
    await api.patch(`/finance/expenses/${expense.id}/splits/${split.id}/settle`);
  }
  await loadAll();
}

// ─── Payment Actions ──────────────────────────────────────────────

function openPaymentDialog() {
  paymentForm.value = {
    to_user_id: null,
    amount: null,
    method: "cash",
    description: "",
    payment_date: new Date().toISOString().split("T")[0],
  };
  showPaymentDialog.value = true;
}

async function savePayment() {
  if (!paymentForm.value.amount || !paymentForm.value.to_user_id) return;
  const data: any = {
    to_user_id: paymentForm.value.to_user_id,
    amount_cents: Math.round(paymentForm.value.amount * 100),
    method: paymentForm.value.method,
    payment_date: paymentForm.value.payment_date,
  };
  if (paymentForm.value.description) data.description = paymentForm.value.description;

  await api.post("/finance/payments/", data);
  showPaymentDialog.value = false;
  await loadAll();
}
async function confirmPayment(id: number) {
  await api.patch(`/finance/payments/${id}`, { confirmed_by_admin: true });
  await loadAll();
}

async function deletePayment(id: number) {
  await api.delete(`/finance/payments/${id}`);
  await loadAll();
}

// ─── Category Actions ─────────────────────────────────────────────

function openCategoryDialog() {
  categoryForm.value = { name: "", icon: "" };
  showCategoryDialog.value = true;
}

async function saveCategory() {
  if (!categoryForm.value.name) return;
  const data: any = { name: categoryForm.value.name };
  if (categoryForm.value.icon) data.icon = categoryForm.value.icon;
  await api.post("/finance/categories/", data);
  showCategoryDialog.value = false;
  await loadAll();
}

// ─── Receipt photo attached to expense form ───────────────────────

function onReceiptUploaded(data: { path: string; filename: string }) {
  expenseForm.value.receipt_image_path = data.path;
}
</script>

<template>
  <div>
    <h1 class="text-h4 mb-4">Finanzen</h1>

    <!-- ─── Balance Overview (always visible) ──────────────────── -->
    <v-card class="mb-6" v-if="balance">
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-scale-balance" class="mr-2" />
        Kontostand
        <v-spacer />
        <v-chip variant="tonal">
          Gesamt: {{ formatEuro(balance.total_expenses_cents) }}
        </v-chip>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col
            v-for="b in balance.balances"
            :key="b.user_id"
            cols="6"
            sm="4"
            md="3"
          >
            <v-card :color="balanceColor(b.balance_cents)" variant="tonal">
              <v-card-text class="text-center pa-3">
                <div class="text-body-2 font-weight-bold">{{ b.display_name }}</div>
                <div class="text-h5 font-weight-bold mt-1">
                  {{ formatEuro(b.balance_cents) }}
                </div>
                <div class="text-caption">
                  {{ b.balance_cents > 0 ? "bekommt noch" : b.balance_cents < 0 ? "schuldet noch" : "ausgeglichen" }}
                </div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- ─── Action Buttons ─────────────────────────────────────── -->
    <div class="d-flex ga-2 mb-4 flex-wrap">
      <v-btn color="primary" prepend-icon="mdi-plus" size="large" @click="openExpenseDialog">
        Ausgabe erfassen
      </v-btn>
      <v-btn color="secondary" prepend-icon="mdi-cash" variant="tonal" @click="openPaymentDialog">
        Zahlung erfassen
      </v-btn>
      <v-btn color="default" prepend-icon="mdi-tag-plus" variant="outlined" size="small" @click="openCategoryDialog">
        Kategorie
      </v-btn>
    </div>

    <!-- ─── Tabs ───────────────────────────────────────────────── -->
    <v-tabs v-model="tab" color="primary" class="mb-4">
      <v-tab value="expenses">
        <v-icon start icon="mdi-receipt" />
        Ausgaben ({{ expenses.length }})
      </v-tab>
      <v-tab value="payments">
        <v-icon start icon="mdi-cash-multiple" />
        Zahlungen ({{ payments.length }})
      </v-tab>
    </v-tabs>

    <v-skeleton-loader v-if="loading" type="card@3" />

    <!-- ─── Expenses Tab ───────────────────────────────────────── -->
    <v-window v-model="tab">
      <v-window-item value="expenses">
        <div v-if="expenses.length === 0" class="text-center py-12">
          <v-icon icon="mdi-receipt-text-outline" size="80" color="grey" />
          <p class="text-h6 text-grey mt-4">Noch keine Ausgaben erfasst</p>
        </div>

        <v-card v-for="expense in expenses" :key="expense.id" class="mb-3">
          <v-card-title class="d-flex align-center">
            <v-chip
              v-if="expense.category"
              size="small"
              color="primary"
              variant="tonal"
              class="mr-2"
            >
              {{ expense.category.icon || "📁" }} {{ expense.category.name }}
            </v-chip>
            <span class="font-weight-bold">{{ expense.description }}</span>
            <v-spacer />
            <span class="text-h6 font-weight-bold text-primary">
              {{ formatEuro(expense.amount_cents) }}
            </span>
          </v-card-title>

          <v-card-subtitle class="d-flex align-center ga-2">
            <v-icon icon="mdi-account" size="small" />
            {{ expense.user.display_name }}
            <v-icon icon="mdi-calendar" size="small" class="ml-2" />
            {{ new Date(expense.expense_date).toLocaleDateString("de-DE") }}
            <v-icon
              v-if="expense.receipt_image_path"
              icon="mdi-camera"
              size="small"
              color="primary"
              class="ml-2"
            />
          </v-card-subtitle>

          <v-card-text v-if="expense.notes" class="text-body-2 pt-1 pb-0">
            {{ expense.notes }}
          </v-card-text>

          <!-- Receipt preview -->
          <v-card-text v-if="expense.receipt_image_path" class="pt-2 pb-0">
            <v-img
              :src="`/api/finance/receipts/${expense.receipt_image_path.replace('receipts/', '')}`"
              max-height="120"
              max-width="200"
              rounded="lg"
              cover
            />
          </v-card-text>

          <!-- Splits -->
          <v-card-text class="pt-2">
            <div class="text-caption text-medium-emphasis mb-1">Aufteilung:</div>
            <v-chip
              v-for="split in expense.splits"
              :key="split.id"
              size="small"
              :color="split.is_settled ? 'success' : 'default'"
              :variant="split.is_settled ? 'flat' : 'outlined'"
              class="mr-1 mb-1"
              @click="toggleSettle(expense, split)"
              style="cursor: pointer"
            >
              <v-icon
                start
                :icon="split.is_settled ? 'mdi-check-circle' : 'mdi-circle-outline'"
                size="small"
              />
              {{ split.user.display_name }}: {{ formatEuro(split.share_amount_cents) }}
            </v-chip>
          </v-card-text>

          <v-card-actions>
            <v-spacer />
            <v-btn
              size="small"
              color="error"
              variant="text"
              icon="mdi-delete"
              @click="deleteExpense(expense.id)"
            />
          </v-card-actions>
        </v-card>
      </v-window-item>

      <!-- ─── Payments Tab ───────────────────────────────────── -->
      <v-window-item value="payments">
        <div v-if="payments.length === 0" class="text-center py-12">
          <v-icon icon="mdi-cash-remove" size="80" color="grey" />
          <p class="text-h6 text-grey mt-4">Noch keine Zahlungen erfasst</p>
        </div>

        <v-card v-for="payment in payments" :key="payment.id" class="mb-3">
          <v-list-item>
            <template #prepend>
              <v-avatar color="info" variant="tonal">
                <v-icon icon="mdi-cash" />
              </v-avatar>
            </template>

            <template #title>
              <span class="font-weight-bold">
                {{ payment.from_user.display_name }}
              </span>
              →
              <span class="font-weight-bold">
                {{ payment.to_user.display_name }}
              </span>
              <span class="text-primary font-weight-bold ml-2">
                {{ formatEuro(payment.amount_cents) }}
              </span>
            </template>

            <template #subtitle>
              {{ new Date(payment.payment_date).toLocaleDateString("de-DE") }}
              · {{ methodLabel(payment.method) }}
              <span v-if="payment.description"> · {{ payment.description }}</span>
            </template>

            <template #append>
              <v-chip
                v-if="payment.confirmed_by_admin"
                size="small"
                color="success"
                variant="flat"
              >
                <v-icon start icon="mdi-check" size="small" />
                Bestätigt
              </v-chip>
              <v-btn
                v-else-if="auth.isAdmin"
                size="small"
                color="success"
                variant="tonal"
                @click="confirmPayment(payment.id)"
              >
                Bestätigen
              </v-btn>
              <v-chip v-else size="small" color="warning" variant="tonal">
                Offen
              </v-chip>
              <v-btn
                size="small"
                color="error"
                variant="text"
                icon="mdi-delete"
                class="ml-1"
                @click="deletePayment(payment.id)"
              />
            </template>
          </v-list-item>
        </v-card>
      </v-window-item>
    </v-window>

    <!-- ═══ Expense Dialog ═══════════════════════════════════════ -->
    <v-dialog v-model="showExpenseDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon icon="mdi-receipt" class="mr-2" />
          Ausgabe erfassen
        </v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveExpense">
            <!-- Amount: BIG input, autofocus -->
            <v-text-field
              v-model.number="expenseForm.amount"
              label="Betrag (€) *"
              type="number"
              min="0.01"
              step="0.01"
              prefix="€"
              autofocus
              class="mb-2 text-h5"
              inputmode="decimal"
            />

            <v-text-field
              v-model="expenseForm.description"
              label="Beschreibung *"
              placeholder="z.B. Baumarkt Erde 20L"
              class="mb-2"
            />

            <v-select
              v-model="expenseForm.category_id"
              label="Kategorie"
              :items="categories.filter(c => c.is_active)"
              :item-title="(c: Category) => (c.icon ? c.icon + ' ' : '') + c.name"
              item-value="id"
              clearable
              class="mb-2"
            />

            <v-text-field
              v-model="expenseForm.expense_date"
              label="Datum"
              type="date"
              class="mb-2"
            />

            <!-- Receipt Photo -->
            <div class="text-body-2 text-medium-emphasis mb-1">Kassenbon / Rechnung:</div>
            <PhotoCapture
              v-model="expenseForm.receipt_image_path"
              label="Beleg fotografieren"
              @uploaded="onReceiptUploaded"
            />

            <v-textarea
              v-model="expenseForm.notes"
              label="Notizen"
              rows="2"
              class="mt-2"
            />

            <v-alert type="info" variant="tonal" density="compact" class="mt-2">
              Wird automatisch gleichmäßig auf alle Mitglieder aufgeteilt.
            </v-alert>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showExpenseDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            size="large"
            :disabled="!expenseForm.amount || !expenseForm.description"
            @click="saveExpense"
          >
            <v-icon start icon="mdi-check" />
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Payment Dialog ═══════════════════════════════════════ -->
    <v-dialog v-model="showPaymentDialog" max-width="500">
      <v-card>
        <v-card-title>
          <v-icon icon="mdi-cash" class="mr-2" />
          Zahlung erfassen
        </v-card-title>
        <v-card-text>
          <v-form @submit.prevent="savePayment">
            <v-select
              v-model="paymentForm.to_user_id"
              label="Zahlung an *"
              :items="otherUsers"
              item-title="display_name"
              item-value="id"
              class="mb-2"
            />

            <v-text-field
              v-model.number="paymentForm.amount"
              label="Betrag (€) *"
              type="number"
              min="0.01"
              step="0.01"
              prefix="€"
              inputmode="decimal"
              class="mb-2"
            />

            <v-radio-group v-model="paymentForm.method" inline label="Methode" class="mb-2">
              <v-radio label="Bar" value="cash" />
              <v-radio label="Überweisung" value="transfer" />
              <v-radio label="Sachleistung" value="material" />
            </v-radio-group>

            <v-text-field
              v-model="paymentForm.payment_date"
              label="Datum"
              type="date"
              class="mb-2"
            />

            <v-text-field
              v-model="paymentForm.description"
              label="Beschreibung"
              placeholder="z.B. Ausgleich April"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showPaymentDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            size="large"
            :disabled="!paymentForm.amount || !paymentForm.to_user_id"
            @click="savePayment"
          >
            <v-icon start icon="mdi-check" />
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Category Dialog ══════════════════════════════════════ -->
    <v-dialog v-model="showCategoryDialog" max-width="400">
      <v-card>
        <v-card-title>Neue Kategorie</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveCategory">
            <v-text-field
              v-model="categoryForm.name"
              label="Name *"
              placeholder="z.B. Saatgut"
              autofocus
              class="mb-2"
            />
            <v-text-field
              v-model="categoryForm.icon"
              label="Icon (Emoji)"
              placeholder="z.B. 🌱"
              maxlength="5"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCategoryDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!categoryForm.name" @click="saveCategory">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

