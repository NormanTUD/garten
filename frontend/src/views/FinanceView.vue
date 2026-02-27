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

interface RecurringCost {
  id: number;
  category: { id: number; name: string; icon: string | null } | null;
  description: string;
  amount_cents: number;
  interval: string;
  is_active: boolean;
  notes: string | null;
}

interface GardenExpense {
  id: number;
  user: { id: number; display_name: string };
  category: { id: number; name: string; icon: string | null } | null;
  amount_cents: number;
  description: string;
  expense_date: string;
  is_shared: boolean;
  receipt_image_path: string | null;
  notes: string | null;
}

interface MemberPayment {
  id: number;
  user: { id: number; display_name: string };
  for_user: { id: number; display_name: string } | null;
  for_user_id: number | null;
  amount_cents: number;
  payment_type: string;
  description: string | null;
  payment_date: string;
  receipt_image_path: string | null;
  confirmed_by_admin: boolean;
  notes: string | null;
}

interface MemberBalance {
  user_id: number;
  display_name: string;
  total_paid_cents: number;
  share_recurring_cents: number;
  share_onetime_cents: number;
  share_total_cents: number;
  remaining_cents: number;
}

interface FundOverview {
  total_recurring_monthly_cents: number;
  total_recurring_yearly_cents: number;
  total_recurring_annual_cents: number;
  total_onetime_expenses_cents: number;
  total_costs_annual_cents: number;
  total_payments_cents: number;
  fund_balance_cents: number;
  share_per_member_annual_cents: number;
  share_per_member_monthly_cents: number;
  member_count: number;
  member_balances: MemberBalance[];
}

// ─── State ────────────────────────────────────────────────────────

const tab = ref("expenses");
const loading = ref(true);

const categories = ref<Category[]>([]);
const recurring = ref<RecurringCost[]>([]);
const expenses = ref<GardenExpense[]>([]);
const payments = ref<MemberPayment[]>([]);
const fund = ref<FundOverview | null>(null);
interface UserInfo {
  id: number;
  username: string;
  display_name: string;
}

const users = ref<UserInfo[]>([]);

// Expense quick-entry
const showExpenseDialog = ref(false);
const expenseForm = ref({
  amount: null as number | null,
  description: "",
  category_name: "",
  expense_date: new Date().toISOString().split("T")[0],
  is_shared: true,
  receipt_image_path: null as string | null,
  notes: "",
});

// Payment quick-entry
const showPaymentDialog = ref(false);
const paymentForm = ref({
  amount: null as number | null,
  payment_type: "cash",
  for_user_id: null as number | null,
  description: "",
  payment_date: new Date().toISOString().split("T")[0],
  receipt_image_path: null as string | null,
});

// Recurring cost form (admin)
const showRecurringDialog = ref(false);
const recurringForm = ref({
  description: "",
  amount: null as number | null,
  interval: "monthly",
  notes: "",
});

// ─── Computed ─────────────────────────────────────────────────────

const categoryNames = computed(() =>
  categories.value.filter((c) => c.is_active).map((c) => (c.icon ? c.icon + " " : "") + c.name)
);

const myBalance = computed(() => {
  if (!fund.value || !auth.user) return null;
  return fund.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
});

// ─── Load Data ────────────────────────────────────────────────────

onMounted(() => loadAll());

async function loadAll() {
  loading.value = true;
  try {
    const [cats, rec, exps, pays, f] = await Promise.all([
      api.get<Category[]>("/finance/categories/"),
      api.get<RecurringCost[]>("/finance/recurring/"),
      api.get<GardenExpense[]>("/finance/expenses/"),
      api.get<MemberPayment[]>("/finance/payments/"),
      api.get<FundOverview>("/finance/fund/"),
    ]);
    categories.value = cats;
    recurring.value = rec;
    expenses.value = exps;
    payments.value = pays;
    fund.value = f;

    // Extract users from balance (works for all users)
    users.value = f.member_balances.map((b) => ({
      id: b.user_id,
      username: "",
      display_name: b.display_name,
    }));
  } finally {
    loading.value = false;
  }
}

// ─── Helpers ──────────────────────────────────────────────────────

function eur(cents: number): string {
  return (cents / 100).toLocaleString("de-DE", { style: "currency", currency: "EUR" });
}

function balanceColor(remaining: number): string {
  if (remaining > 0) return "error";
  if (remaining < 0) return "success";
  return "default";
}

function balanceText(remaining: number): string {
  if (remaining > 0) return "schuldet noch";
  if (remaining < 0) return "hat überzahlt";
  return "ausgeglichen ✓";
}

function paymentTypeLabel(t: string): string {
  return { cash: "💵 Bar", transfer: "🏦 Überweisung", material: "🛒 Sachleistung" }[t] || t;
}

function intervalLabel(i: string): string {
  return { monthly: "monatlich", yearly: "jährlich" }[i] || i;
}

// ─── Expense Actions ──────────────────────────────────────────────

function openExpenseDialog() {
  expenseForm.value = {
    amount: null,
    description: "",
    category_name: "",
    expense_date: new Date().toISOString().split("T")[0],
    is_shared: true,
    receipt_image_path: null,
    notes: "",
  };
  showExpenseDialog.value = true;
}

async function saveExpense() {
  if (!expenseForm.value.amount || !expenseForm.value.description) return;

  const data: any = {
    amount_cents: Math.round(expenseForm.value.amount * 100),
    description: expenseForm.value.description,
    expense_date: expenseForm.value.expense_date,
    is_shared: expenseForm.value.is_shared,
  };

  if (expenseForm.value.category_name) {
    const raw = expenseForm.value.category_name.trim();
    const existing = categories.value.find(
      (c) => (c.icon ? c.icon + " " : "") + c.name === raw
    );
    if (existing) {
      data.category_id = existing.id;
    } else {
      data.category_name = raw;
    }
  }

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

// ─── Payment Actions ──────────────────────────────────────────────

function openPaymentDialog() {
  paymentForm.value = {
    amount: null,
    payment_type: "cash",
    for_user_id: null,
    description: "",
    payment_date: new Date().toISOString().split("T")[0],
    receipt_image_path: null,
  };
  showPaymentDialog.value = true;
}

async function savePayment() {
  if (!paymentForm.value.amount) return;

  const data: any = {
    amount_cents: Math.round(paymentForm.value.amount * 100),
    payment_type: paymentForm.value.payment_type,
    payment_date: paymentForm.value.payment_date,
  };
  if (paymentForm.value.for_user_id) data.for_user_id = paymentForm.value.for_user_id;
  if (paymentForm.value.description) data.description = paymentForm.value.description;
  if (paymentForm.value.receipt_image_path) data.receipt_image_path = paymentForm.value.receipt_image_path;

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

// ─── Recurring Cost Actions ───────────────────────────────────────

function openRecurringDialog() {
  recurringForm.value = { description: "", amount: null, interval: "monthly", notes: "" };
  showRecurringDialog.value = true;
}

async function saveRecurring() {
  if (!recurringForm.value.amount || !recurringForm.value.description) return;
  await api.post("/finance/recurring/", {
    description: recurringForm.value.description,
    amount_cents: Math.round(recurringForm.value.amount * 100),
    interval: recurringForm.value.interval,
    notes: recurringForm.value.notes || undefined,
  });
  showRecurringDialog.value = false;
  await loadAll();
}

async function deleteRecurring(id: number) {
  await api.delete(`/finance/recurring/${id}`);
  await loadAll();
}
</script>

<template>
  <div>
    <h1 class="text-h4 mb-2">Gartenkasse</h1>

    <v-skeleton-loader v-if="loading" type="card@2" />

    <template v-else>
      <!-- ═══ My Balance (prominent) ═══════════════════════════ -->
      <v-card
        v-if="myBalance"
        :color="balanceColor(myBalance.remaining_cents)"
        variant="tonal"
        class="mb-4"
      >
        <v-card-text class="text-center pa-4">
          <div class="text-body-1">Dein Stand</div>
          <div class="text-h3 font-weight-bold my-2">
            {{ eur(Math.abs(myBalance.remaining_cents)) }}
          </div>
          <div class="text-body-1">
            {{ balanceText(myBalance.remaining_cents) }}
          </div>
          <div class="text-caption mt-1">
            Soll: {{ eur(myBalance.share_total_cents) }} · Bezahlt: {{ eur(myBalance.total_paid_cents) }}
          </div>
          <div class="text-caption">
            ({{ eur(myBalance.share_recurring_cents) }} laufend + {{ eur(myBalance.share_onetime_cents) }} Einmal-Umlagen)
          </div>
        </v-card-text>
      </v-card>

      <!-- ═══ Fund Summary ═════════════════════════════════════ -->
      <v-card class="mb-4" v-if="fund">
        <v-card-text>
          <v-row dense>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Grundbeitrag/Monat</div>
              <div class="text-h6 font-weight-bold">{{ eur(fund.share_recurring_per_member_monthly_cents) }}</div>
              <div class="text-caption text-medium-emphasis">nur laufende Kosten</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Gesamt-Soll/Person</div>
              <div class="text-h6 font-weight-bold">{{ eur(fund.share_total_per_member_annual_cents) }}</div>
              <div class="text-caption text-medium-emphasis">inkl. Einmal-Umlagen</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Eingezahlt gesamt</div>
              <div class="text-h6 font-weight-bold text-success">{{ eur(fund.total_payments_cents) }}</div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Kassenstand</div>
              <div class="text-h6 font-weight-bold" :class="fund.fund_balance_cents >= 0 ? 'text-success' : 'text-error'">
                {{ eur(fund.fund_balance_cents) }}
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <!-- Kostenaufstellung (aufklappbar) -->
        <v-divider />
        <v-expansion-panels variant="accordion" flat>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon icon="mdi-calculator" size="small" class="mr-2" />
              <span class="text-body-2">So setzt sich "Pro Person/Monat" zusammen</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <!-- Laufende monatliche Kosten -->
              <div class="text-subtitle-2 font-weight-bold mb-2">
                <v-icon icon="mdi-repeat" size="small" class="mr-1" />
                Laufende Kosten
              </div>

              <div v-if="recurring.length === 0" class="text-body-2 text-grey mb-3">
                Keine laufenden Kosten eingetragen.
              </div>

              <v-table v-else density="compact" class="mb-3">
                <thead>
                  <tr>
                    <th>Posten</th>
                    <th class="text-right">Betrag</th>
                    <th class="text-right">Intervall</th>
                    <th class="text-right">Pro Jahr</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="r in recurring" :key="r.id">
                    <td>{{ r.description }}</td>
                    <td class="text-right">{{ eur(r.amount_cents) }}</td>
                    <td class="text-right">{{ intervalLabel(r.interval) }}</td>
                    <td class="text-right font-weight-bold">
                      {{ eur(r.interval === "monthly" ? r.amount_cents * 12 : r.amount_cents) }}
                      <v-btn
                        v-if="auth.isAdmin"
                        size="x-small"
                        icon="mdi-delete"
                        variant="text"
                        color="error"
                        density="compact"
                        class="ml-1"
                        @click="deleteRecurring(r.id)"
                      />
                    </td>
                  </tr>
                  <tr class="bg-grey-lighten-4">
                    <td colspan="3" class="font-weight-bold">Summe laufende Kosten / Jahr</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_recurring_annual_cents) }}</td>
                  </tr>
                </tbody>
              </v-table>

              <!-- Einzelposten dieses Jahr -->
              <div class="text-subtitle-2 font-weight-bold mb-2">
                <v-icon icon="mdi-receipt" size="small" class="mr-1" />
                Einzelposten ({{ new Date().getFullYear() }})
              </div>

              <div v-if="fund.total_onetime_expenses_cents === 0" class="text-body-2 text-grey mb-3">
                Keine Einzelposten dieses Jahr.
              </div>

              <v-table v-else density="compact" class="mb-3">
                <thead>
                  <tr>
                    <th>Datum</th>
                    <th>Posten</th>
                    <th>Von</th>
                    <th class="text-right">Betrag</th>
                  </tr>
                </thead>
                <tbody>
		    <tr v-for="e in expenses" :key="e.id">
                    <td>{{ new Date(e.expense_date).toLocaleDateString("de-DE") }}</td>
                    <td>
                      {{ e.description }}
                      <v-chip v-if="e.category" size="x-small" class="ml-1" variant="tonal">
                        {{ e.category.icon || "" }} {{ e.category.name }}
                      </v-chip>
                    </td>
                    <td>{{ e.user.display_name }}</td>
                    <td class="text-right font-weight-bold">
                      {{ eur(e.amount_cents) }}
                      <v-btn
                        v-if="auth.isAdmin"
                        size="x-small"
                        icon="mdi-delete"
                        variant="text"
                        color="error"
                        density="compact"
                        class="ml-1"
                        @click="deleteExpense(e.id)"
                      />
                    </td>
                  </tr>

                  <tr class="bg-grey-lighten-4">
                    <td colspan="3" class="font-weight-bold">Summe Einzelposten</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_onetime_expenses_cents) }}</td>
                  </tr>
                </tbody>
              </v-table>

              <!-- Gesamtrechnung -->
              <v-divider class="mb-3" />
              <div class="text-subtitle-2 font-weight-bold mb-2">
                <v-icon icon="mdi-sigma" size="small" class="mr-1" />
                Gesamtrechnung {{ new Date().getFullYear() }}
              </div>
              <v-table density="compact">
                <tbody>
                  <tr>
                    <td>Laufende Kosten / Jahr</td>
                    <td class="text-right">{{ eur(fund.total_recurring_annual_cents) }}</td>
                    <td class="text-right text-medium-emphasis">
                      pro Person: {{ eur(fund.share_recurring_per_member_annual_cents) }}
                    </td>
                  </tr>
                  <tr>
                    <td>+ Einmal-Ausgaben {{ new Date().getFullYear() }}</td>
                    <td class="text-right">{{ eur(fund.total_onetime_expenses_cents) }}</td>
                    <td class="text-right text-medium-emphasis">
                      pro Person: {{ eur(fund.share_onetime_per_member_cents) }}
                    </td>
                  </tr>
                  <tr class="bg-grey-lighten-4">
                    <td class="font-weight-bold">= Gesamtkosten / Jahr</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_costs_annual_cents) }}</td>
                    <td class="text-right font-weight-bold">
                      pro Person: {{ eur(fund.share_total_per_member_annual_cents) }}
                    </td>
                  </tr>
                  <tr>
                    <td colspan="2"></td>
                    <td></td>
                  </tr>
                  <tr class="bg-primary-lighten-5">
                    <td class="font-weight-bold text-primary" colspan="2">
                      Grundbeitrag (nur laufende Kosten)
                    </td>
                    <td class="text-right font-weight-bold text-primary text-h6">
                      {{ eur(fund.share_recurring_per_member_monthly_cents) }} / Monat
                    </td>
                  </tr>
                  <tr v-if="fund.share_onetime_per_member_cents > 0">
                    <td class="text-medium-emphasis" colspan="2">
                      + Einmal-Umlage ({{ new Date().getFullYear() }})
                    </td>
                    <td class="text-right font-weight-bold">
                      {{ eur(fund.share_onetime_per_member_cents) }} einmalig
                    </td>
                  </tr>
                  <tr class="bg-primary-lighten-5">
                    <td class="font-weight-bold text-primary" colspan="2">
                      Gesamt-Soll / Person / Jahr
                    </td>
                    <td class="text-right font-weight-bold text-primary text-h6">
                      {{ eur(fund.share_total_per_member_annual_cents) }}
                    </td>
                  </tr>
                </tbody>
              </v-table>
            </v-expansion-panel-text>
          </v-expansion-panel>
        </v-expansion-panels>

        <!-- All members -->
        <v-divider />
        <v-card-text class="pt-2 pb-3">
          <div class="text-caption text-medium-emphasis mb-2">Alle Mitglieder ({{ fund.member_count }})</div>
          <v-chip
            v-for="b in fund.member_balances"
            :key="b.user_id"
            :color="balanceColor(b.remaining_cents)"
            variant="tonal"
            class="mr-2 mb-1"
            size="small"
          >
            {{ b.display_name }}:
            <strong class="ml-1">{{ b.remaining_cents > 0 ? '-' : '+' }}{{ eur(Math.abs(b.remaining_cents)) }}</strong>
          </v-chip>
        </v-card-text>
      </v-card>

      <!-- ═══ Quick Action Buttons ═════════════════════════════ -->
      <div class="d-flex ga-2 mb-4 flex-wrap">
        <v-btn color="primary" size="large" prepend-icon="mdi-plus" @click="openExpenseDialog">
          Ausgabe
        </v-btn>
        <v-btn color="success" size="large" variant="tonal" prepend-icon="mdi-cash-plus" @click="openPaymentDialog">
          Einzahlung
        </v-btn>
        <v-btn
          v-if="auth.isAdmin"
          color="default"
          variant="outlined"
          size="small"
          prepend-icon="mdi-repeat"
          @click="openRecurringDialog"
        >
          Laufende Kosten
        </v-btn>
      </div>

      <!-- ═══ Tabs ═════════════════════════════════════════════ -->
      <v-tabs v-model="tab" color="primary" class="mb-4">
        <v-tab value="expenses">
          <v-icon start icon="mdi-receipt" />
          Ausgaben ({{ expenses.length }})
        </v-tab>
        <v-tab value="payments">
          <v-icon start icon="mdi-cash-multiple" />
          Einzahlungen ({{ payments.length }})
        </v-tab>
        <v-tab value="recurring">
          <v-icon start icon="mdi-repeat" />
          Laufend ({{ recurring.length }})
        </v-tab>
      </v-tabs>

      <v-window v-model="tab">
        <!-- ─── Expenses Tab ─────────────────────────────────── -->
        <v-window-item value="expenses">
          <div v-if="expenses.length === 0" class="text-center py-8">
            <v-icon icon="mdi-receipt-text-outline" size="64" color="grey" />
            <p class="text-body-1 text-grey mt-2">Noch keine Ausgaben</p>
          </div>

          <v-list v-else lines="three">
            <v-list-item v-for="e in expenses" :key="e.id">
              <template #prepend>
                <v-avatar
                  v-if="e.receipt_image_path"
                  rounded="lg"
                  size="48"
                >
                  <v-img :src="`/api/finance/receipts/${e.receipt_image_path.replace('receipts/', '')}`" cover />
                </v-avatar>
                <v-avatar v-else color="primary" variant="tonal" size="48">
                  <v-icon icon="mdi-receipt" />
                </v-avatar>
              </template>

              <template #title>
                <span class="font-weight-bold">{{ e.description }}</span>
                <v-chip v-if="e.category" size="x-small" class="ml-2" variant="tonal">
                  {{ e.category.icon || "" }} {{ e.category.name }}
                </v-chip>
		<v-chip v-if="!e.is_shared" size="x-small" class="ml-1" color="warning" variant="flat">
                  nicht umgelegt
                </v-chip>

              </template>

              <template #subtitle>
                {{ new Date(e.expense_date).toLocaleDateString("de-DE") }}
                · {{ e.user.display_name }}
                <span v-if="e.notes"> · {{ e.notes }}</span>
              </template>

              <template #append>
                <div class="text-right">
                  <div class="text-body-1 font-weight-bold text-primary">{{ eur(e.amount_cents) }}</div>
                  <v-btn v-if="auth.isAdmin" size="x-small" icon="mdi-delete" variant="text" color="error" @click="deleteExpense(e.id)" />
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-window-item>

        <!-- ─── Payments Tab ─────────────────────────────────── -->
        <v-window-item value="payments">
          <div v-if="payments.length === 0" class="text-center py-8">
            <v-icon icon="mdi-cash-remove" size="64" color="grey" />
            <p class="text-body-1 text-grey mt-2">Noch keine Einzahlungen</p>
          </div>

          <v-list v-else lines="three">
            <v-list-item v-for="p in payments" :key="p.id">
              <template #prepend>
                <v-avatar
                  v-if="p.receipt_image_path"
                  rounded="lg"
                  size="48"
                >
                  <v-img :src="`/api/finance/receipts/${p.receipt_image_path.replace('receipts/', '')}`" cover />
                </v-avatar>
                <v-avatar v-else color="success" variant="tonal" size="48">
                  <v-icon icon="mdi-cash-plus" />
                </v-avatar>
              </template>

	      <template #title>
                <span class="font-weight-bold">
                  {{ p.for_user ? p.for_user.display_name : p.user.display_name }}
                </span>
                <v-chip v-if="p.for_user && p.for_user.id !== p.user.id" size="x-small" class="ml-1" variant="tonal">
                  eingetragen von {{ p.user.display_name }}
                </v-chip>

                <v-chip
                  v-if="p.confirmed_by_admin"
                  size="x-small"
                  color="success"
                  variant="flat"
                  class="ml-1"
                >
                  ✓ Bestätigt
                </v-chip>
              </template>

              <template #subtitle>
                {{ new Date(p.payment_date).toLocaleDateString("de-DE") }}
                <span v-if="p.description"> · {{ p.description }}</span>
              </template>

              <template #append>
                <div class="text-right">
                  <div class="text-body-1 font-weight-bold text-success">{{ eur(p.amount_cents) }}</div>
                  <div class="d-flex ga-1 justify-end mt-1">
                    <v-btn
                      v-if="auth.isAdmin && !p.confirmed_by_admin"
                      size="x-small"
                      color="success"
                      variant="tonal"
                      @click="confirmPayment(p.id)"
                    >
                      Bestätigen
                    </v-btn>
		    <v-btn v-if="auth.isAdmin" size="x-small" icon="mdi-delete" variant="text" color="error" @click="deletePayment(p.id)" />
                  </div>
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-window-item>

        <!-- ─── Recurring Costs Tab ──────────────────────────── -->
        <v-window-item value="recurring">
          <div v-if="recurring.length === 0" class="text-center py-8">
            <v-icon icon="mdi-repeat-off" size="64" color="grey" />
            <p class="text-body-1 text-grey mt-2">Keine laufenden Kosten eingetragen</p>
            <v-btn
              v-if="auth.isAdmin"
              color="primary"
              variant="tonal"
              class="mt-2"
              @click="openRecurringDialog"
            >
              Erste laufende Kosten anlegen
            </v-btn>
          </div>

          <v-list v-else>
            <v-list-item v-for="r in recurring" :key="r.id">
              <template #prepend>
                <v-avatar color="warning" variant="tonal">
                  <v-icon icon="mdi-repeat" />
                </v-avatar>
              </template>

              <template #title>
                <span class="font-weight-bold">{{ r.description }}</span>
              </template>

              <template #subtitle>
                {{ intervalLabel(r.interval) }}
                <span v-if="r.notes"> · {{ r.notes }}</span>
              </template>

              <template #append>
                <div class="text-right">
                  <div class="text-body-1 font-weight-bold">{{ eur(r.amount_cents) }}</div>
                  <div class="text-caption text-medium-emphasis">
                    {{ r.interval === "monthly" ? eur(r.amount_cents * 12) + "/Jahr" : eur(r.amount_cents) + "/Jahr" }}
                  </div>
                  <v-btn
                    v-if="auth.isAdmin"
                    size="x-small"
                    icon="mdi-delete"
                    variant="text"
                    color="error"
                    @click="deleteRecurring(r.id)"
                  />
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-window-item>
      </v-window>
    </template>

    <!-- ═══ Expense Dialog (Quick Entry) ═══════════════════════ -->
    <v-dialog v-model="showExpenseDialog" max-width="500" eager>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi-receipt" class="mr-2" />
          Ausgabe erfassen
        </v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveExpense">
            <v-text-field
              v-model.number="expenseForm.amount"
              label="Betrag (€) *"
              type="number"
              min="0.01"
              step="0.01"
              prefix="€"
              autofocus
              inputmode="decimal"
              variant="outlined"
              density="comfortable"
              class="mb-3 text-h5"
            />

            <v-text-field
              v-model="expenseForm.description"
              label="Wofür? *"
              placeholder="z.B. Baumarkt Erde 20L"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />

            <v-combobox
              v-model="expenseForm.category_name"
              label="Kategorie"
              :items="categoryNames"
              placeholder="Tippen oder wählen..."
              clearable
              variant="outlined"
              density="comfortable"
              class="mb-3"
              hint="Neue Kategorie? Einfach eintippen!"
              persistent-hint
            />

            <v-text-field
              v-model="expenseForm.expense_date"
              label="Datum"
              type="date"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />
            <v-checkbox
              v-model="expenseForm.is_shared"
              label="Auf alle Mitglieder umlegen"
              hint="Wenn deaktiviert, wird dieser Posten nicht in die Jahreskosten eingerechnet"
              persistent-hint
              color="primary"
              class="mb-3"
            />

            <div class="text-body-2 text-medium-emphasis mb-1">Kassenbon / Rechnung:</div>
            <PhotoCapture
              v-model="expenseForm.receipt_image_path"
              label="Beleg fotografieren"
            />

            <v-textarea
              v-model="expenseForm.notes"
              label="Notizen"
              rows="2"
              variant="outlined"
              density="comfortable"
              class="mt-3"
            />
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

    <!-- ═══ Payment Dialog (Quick Entry) ═══════════════════════ -->
    <v-dialog v-model="showPaymentDialog" max-width="500" eager>
      <v-card>
        <v-card-title class="d-flex align-center">
          <v-icon icon="mdi-cash-plus" class="mr-2" color="success" />
          Einzahlung in die Gartenkasse
        </v-card-title>
        <v-card-text>
          <v-form @submit.prevent="savePayment">
            <v-text-field
              v-model.number="paymentForm.amount"
              label="Betrag (€) *"
              type="number"
              min="0.01"
              step="0.01"
              prefix="€"
              autofocus
              inputmode="decimal"
              variant="outlined"
              density="comfortable"
              class="mb-3 text-h5"
            />

            <!-- Admin: für wen? -->
            <v-select
              v-if="auth.isAdmin"
              v-model="paymentForm.for_user_id"
              label="Einzahlung für"
              :items="users"
              item-title="display_name"
              item-value="id"
              clearable
              variant="outlined"
              density="comfortable"
              class="mb-3"
              hint="Leer = für dich selbst"
              persistent-hint
            />

            <v-btn-toggle
              v-model="paymentForm.payment_type"
              mandatory
              color="primary"
              class="mb-3"
              density="comfortable"
            >
              <v-btn value="cash">💵 Bar</v-btn>
              <v-btn value="transfer">🏦 Überweisung</v-btn>
              <v-btn value="material">🛒 Sachleistung</v-btn>
            </v-btn-toggle>

            <v-text-field
              v-model="paymentForm.payment_date"
              label="Datum"
              type="date"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />

            <v-text-field
              v-model="paymentForm.description"
              label="Beschreibung"
              :placeholder="paymentForm.payment_type === 'material' ? 'z.B. Erde mitgebracht' : 'optional'"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />

            <template v-if="paymentForm.payment_type === 'material'">
              <div class="text-body-2 text-medium-emphasis mb-1">Beleg / Rechnung:</div>
              <PhotoCapture
                v-model="paymentForm.receipt_image_path"
                label="Beleg fotografieren"
              />
            </template>

            <v-alert
              v-if="myBalance && myBalance.remaining_cents > 0"
              type="info"
              variant="tonal"
              density="compact"
              class="mt-3"
            >
              Du schuldest noch {{ eur(myBalance.remaining_cents) }} für dieses Jahr.
            </v-alert>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showPaymentDialog = false">Abbrechen</v-btn>
          <v-btn
            color="success"
            size="large"
            :disabled="!paymentForm.amount"
            @click="savePayment"
          >
            <v-icon start icon="mdi-check" />
            Einzahlen
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Recurring Cost Dialog (Admin) ══════════════════════ -->
    <v-dialog v-model="showRecurringDialog" max-width="500">
      <v-card>
        <v-card-title>Laufende Kosten anlegen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveRecurring">
            <v-text-field
              v-model="recurringForm.description"
              label="Beschreibung *"
              placeholder="z.B. Pacht, Wasser, Versicherung"
              autofocus
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />

            <v-text-field
              v-model.number="recurringForm.amount"
              label="Betrag (€) *"
              type="number"
              min="0.01"
              step="0.01"
              prefix="€"
              inputmode="decimal"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />

            <v-btn-toggle
              v-model="recurringForm.interval"
              mandatory
              color="primary"
              class="mb-3"
              density="comfortable"
            >
              <v-btn value="monthly">Monatlich</v-btn>
              <v-btn value="yearly">Jährlich</v-btn>
            </v-btn-toggle>

            <v-textarea
              v-model="recurringForm.notes"
              label="Notizen"
              rows="2"
              variant="outlined"
              density="comfortable"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRecurringDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            :disabled="!recurringForm.amount || !recurringForm.description"
            @click="saveRecurring"
          >
            Speichern
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

