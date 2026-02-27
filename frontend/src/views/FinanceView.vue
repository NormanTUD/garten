<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
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
  valid_from: string;
  valid_to: string | null;
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
  confirmed_by_admin: boolean;
  confirmed_by_id: number | null;
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

interface StandingOrderSkip {
  id: number;
  standing_order_id: number;
  year: number;
  month: number;
  reason: string | null;
}

interface StandingOrder {
  id: number;
  user: { id: number; display_name: string };
  amount_cents: number;
  description: string | null;
  valid_from: string;
  valid_to: string | null;
  is_active: boolean;
  notes: string | null;
  skips: StandingOrderSkip[];
}

interface MemberBalance {
  user_id: number;
  display_name: string;
  total_paid_cents: number;
  total_standing_order_cents: number;
  total_income_cents: number;
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
  total_standing_order_cents: number;
  total_income_cents: number;
  fund_balance_cents: number;
  share_recurring_per_member_annual_cents: number;
  share_recurring_per_member_monthly_cents: number;
  share_onetime_per_member_cents: number;
  share_total_per_member_annual_cents: number;
  share_total_per_member_monthly_cents: number;
  member_count: number;
  member_balances: MemberBalance[];
}

interface UserInfo {
  id: number;
  username: string;
  display_name: string;
}

// ─── State ────────────────────────────────────────────────────────

const tab = ref("expenses");
const loading = ref(true);
const selectedYear = ref(new Date().getFullYear());

const yearOptions = computed(() => {
  const current = new Date().getFullYear();
  const years = [];
  for (let y = current - 5; y <= current + 2; y++) years.push(y);
  return years;
});

const categories = ref<Category[]>([]);
const recurring = ref<RecurringCost[]>([]);
const expenses = ref<GardenExpense[]>([]);
const payments = ref<MemberPayment[]>([]);
const standingOrders = ref<StandingOrder[]>([]);
const fund = ref<FundOverview | null>(null);
const users = ref<UserInfo[]>([]);

// Forms
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

const showPaymentDialog = ref(false);
const paymentForm = ref({
  amount: null as number | null,
  payment_type: "cash",
  for_user_id: null as number | null,
  description: "",
  payment_date: new Date().toISOString().split("T")[0],
  receipt_image_path: null as string | null,
});

const showRecurringDialog = ref(false);
const recurringForm = ref({
  description: "",
  amount: null as number | null,
  interval: "monthly",
  valid_from: `${new Date().getFullYear()}-01-01`,
  valid_to: "",
  notes: "",
});

const showEditRecurringDialog = ref(false);
const editRecurringForm = ref({
  id: 0,
  description: "",
  amount: null as number | null,
  interval: "monthly",
  valid_from: "",
  valid_to: "",
  notes: "",
});

const showStandingDialog = ref(false);
const standingForm = ref({
  user_id: null as number | null,
  amount: null as number | null,
  description: "",
  valid_from: `${new Date().getFullYear()}-01-01`,
  valid_to: "",
  notes: "",
});

const showEditStandingDialog = ref(false);
const editStandingForm = ref({
  id: 0,
  amount: null as number | null,
  description: "",
  valid_from: "",
  valid_to: "",
  notes: "",
});

const showSkipDialog = ref(false);
const skipForm = ref({
  order_id: 0,
  order_description: "",
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1,
  reason: "",
});

const categoryNames = computed(() =>
  categories.value.filter((c) => c.is_active).map((c) => (c.icon ? c.icon + " " : "") + c.name)
);

const myBalance = computed(() => {
  if (!fund.value || !auth.user) return null;
  return fund.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
});

const monthNames = ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"];

// ─── Load Data ────────────────────────────────────────────────────

onMounted(() => loadAll());
watch(selectedYear, () => loadAll());

async function loadAll() {
  loading.value = true;
  try {
    const [cats, rec, exps, pays, sos, f] = await Promise.all([
      api.get<Category[]>("/finance/categories/"),
      api.get<RecurringCost[]>("/finance/recurring/", { year: selectedYear.value }),
      api.get<GardenExpense[]>("/finance/expenses/", {
        date_from: `${selectedYear.value}-01-01`,
        date_to: `${selectedYear.value}-12-31`,
      }),
      api.get<MemberPayment[]>("/finance/payments/", {
        date_from: `${selectedYear.value}-01-01`,
        date_to: `${selectedYear.value}-12-31`,
      }),
      api.get<StandingOrder[]>("/finance/standing-orders/"),
      api.get<FundOverview>("/finance/fund/", { year: selectedYear.value }),
    ]);
    categories.value = cats;
    recurring.value = rec;
    expenses.value = exps;
    payments.value = pays;
    standingOrders.value = sos;
    fund.value = f;

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

function isMonthSkipped(order: StandingOrder, month: number): boolean {
  return order.skips.some((s) => s.year === selectedYear.value && s.month === month);
}

function getSkipId(order: StandingOrder, month: number): number | null {
  const skip = order.skips.find((s) => s.year === selectedYear.value && s.month === month);
  return skip ? skip.id : null;
}

function orderActiveInMonth(order: StandingOrder, month: number): boolean {
  const from = new Date(order.valid_from);
  const fromMonth = from.getFullYear() * 12 + from.getMonth();
  const checkMonth = selectedYear.value * 12 + (month - 1);
  if (checkMonth < fromMonth) return false;
  if (order.valid_to) {
    const to = new Date(order.valid_to);
    const toMonth = to.getFullYear() * 12 + to.getMonth();
    if (checkMonth > toMonth) return false;
  }
  return true;
}

// ─── Expense Actions ──────────────────────────────────────────────

function openExpenseDialog() {
  expenseForm.value = {
    amount: null, description: "", category_name: "",
    expense_date: new Date().toISOString().split("T")[0],
    is_shared: true, receipt_image_path: null, notes: "",
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
    const existing = categories.value.find((c) => (c.icon ? c.icon + " " : "") + c.name === raw);
    if (existing) data.category_id = existing.id;
    else data.category_name = raw;
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
    amount: null, payment_type: "cash", for_user_id: null,
    description: "", payment_date: new Date().toISOString().split("T")[0],
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
  recurringForm.value = {
    description: "", amount: null, interval: "monthly",
    valid_from: `${selectedYear.value}-01-01`, valid_to: "", notes: "",
  };
  showRecurringDialog.value = true;
}

async function saveRecurring() {
  if (!recurringForm.value.amount || !recurringForm.value.description) return;
  const data: any = {
    description: recurringForm.value.description,
    amount_cents: Math.round(recurringForm.value.amount * 100),
    interval: recurringForm.value.interval,
    valid_from: recurringForm.value.valid_from,
  };
  if (recurringForm.value.valid_to) data.valid_to = recurringForm.value.valid_to;
  if (recurringForm.value.notes) data.notes = recurringForm.value.notes;
  await api.post("/finance/recurring/", data);
  showRecurringDialog.value = false;
  await loadAll();
}

function openEditRecurringDialog(r: RecurringCost) {
  editRecurringForm.value = {
    id: r.id,
    description: r.description,
    amount: r.amount_cents / 100,
    interval: r.interval,
    valid_from: r.valid_from,
    valid_to: r.valid_to || "",
    notes: r.notes || "",
  };
  showEditRecurringDialog.value = true;
}

async function saveEditRecurring() {
  const data: any = {
    description: editRecurringForm.value.description,
    amount_cents: Math.round(editRecurringForm.value.amount! * 100),
    interval: editRecurringForm.value.interval,
    valid_from: editRecurringForm.value.valid_from,
  };
  if (editRecurringForm.value.valid_to) data.valid_to = editRecurringForm.value.valid_to;
  else data.valid_to = null;
  if (editRecurringForm.value.notes) data.notes = editRecurringForm.value.notes;
  await api.patch(`/finance/recurring/${editRecurringForm.value.id}`, data);
  showEditRecurringDialog.value = false;
  await loadAll();
}

async function deleteRecurring(id: number) {
  await api.delete(`/finance/recurring/${id}`);
  await loadAll();
}

// ─── Standing Order Actions ───────────────────────────────────────

function openStandingDialog() {
  standingForm.value = {
    user_id: null, amount: null, description: "",
    valid_from: `${selectedYear.value}-01-01`, valid_to: "", notes: "",
  };
  showStandingDialog.value = true;
}

async function saveStanding() {
  if (!standingForm.value.amount) return;
  const data: any = {
    amount_cents: Math.round(standingForm.value.amount * 100),
    valid_from: standingForm.value.valid_from,
  };
  if (standingForm.value.user_id) data.user_id = standingForm.value.user_id;
  if (standingForm.value.description) data.description = standingForm.value.description;
  if (standingForm.value.valid_to) data.valid_to = standingForm.value.valid_to;
  if (standingForm.value.notes) data.notes = standingForm.value.notes;
  await api.post("/finance/standing-orders/", data);
  showStandingDialog.value = false;
  await loadAll();
}

function openEditStandingDialog(o: StandingOrder) {
  editStandingForm.value = {
    id: o.id,
    amount: o.amount_cents / 100,
    description: o.description || "",
    valid_from: o.valid_from,
    valid_to: o.valid_to || "",
    notes: o.notes || "",
  };
  showEditStandingDialog.value = true;
}

async function saveEditStanding() {
  const data: any = {
    amount_cents: Math.round(editStandingForm.value.amount! * 100),
    valid_from: editStandingForm.value.valid_from,
  };
  if (editStandingForm.value.description) data.description = editStandingForm.value.description;
  if (editStandingForm.value.valid_to) data.valid_to = editStandingForm.value.valid_to;
  else data.valid_to = null;
  if (editStandingForm.value.notes) data.notes = editStandingForm.value.notes;
  await api.patch(`/finance/standing-orders/${editStandingForm.value.id}`, data);
  showEditStandingDialog.value = false;
  await loadAll();
}

async function deleteStanding(id: number) {
  await api.delete(`/finance/standing-orders/${id}`);
  await loadAll();
}

function openSkipDialog(order: StandingOrder) {
  skipForm.value = {
    order_id: order.id,
    order_description: `${order.user.display_name} – ${eur(order.amount_cents)}/Monat`,
    year: selectedYear.value,
    month: new Date().getMonth() + 1,
    reason: "",
  };
  showSkipDialog.value = true;
}

async function saveSkip() {
  await api.post(`/finance/standing-orders/${skipForm.value.order_id}/skip`, {
    year: skipForm.value.year,
    month: skipForm.value.month,
    reason: skipForm.value.reason || undefined,
  });
  showSkipDialog.value = false;
  await loadAll();
}

async function removeSkip(orderId: number, skipId: number) {
  await api.delete(`/finance/standing-orders/${orderId}/skip/${skipId}`);
  await loadAll();
}

async function confirmExpense(id: number) {
  await api.patch(`/finance/expenses/${id}/confirm`);
  await loadAll();
}
</script>

<template>
  <div>
    <!-- Header + Year Selector -->
    <div class="d-flex align-center mb-2 flex-wrap ga-2">
      <h1 class="text-h4">Gartenkasse</h1>
      <v-spacer />
      <v-btn-toggle v-model="selectedYear" mandatory color="primary" density="compact" variant="outlined">
        <v-btn v-for="y in yearOptions" :key="y" :value="y" size="small"
          :variant="y === selectedYear ? 'flat' : 'outlined'">{{ y }}</v-btn>
      </v-btn-toggle>
    </div>

    <v-skeleton-loader v-if="loading" type="card@2" />

    <template v-else>
      <!-- ═══ My Balance ═══════════════════════════════════════ -->
      <v-card v-if="myBalance" :color="balanceColor(myBalance.remaining_cents)" variant="tonal" class="mb-4">
        <v-card-text class="text-center pa-4">
          <div class="text-body-1">Dein Stand {{ selectedYear }}</div>
          <div class="text-h3 font-weight-bold my-2">{{ eur(Math.abs(myBalance.remaining_cents)) }}</div>
          <div class="text-body-1">{{ balanceText(myBalance.remaining_cents) }}</div>
          <div class="text-caption mt-1">
            Soll: {{ eur(myBalance.share_total_cents) }} · Bezahlt: {{ eur(myBalance.total_paid_cents) }}
            · Daueraufträge: {{ eur(myBalance.total_standing_order_cents) }}
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
              <div class="text-caption text-medium-emphasis">Eingegangen gesamt</div>
              <div class="text-h6 font-weight-bold text-success">{{ eur(fund.total_income_cents) }}</div>
              <div class="text-caption text-medium-emphasis">
                {{ eur(fund.total_payments_cents) }} Zahlungen + {{ eur(fund.total_standing_order_cents) }} Daueraufträge
              </div>
            </v-col>
            <v-col cols="6" sm="3">
              <div class="text-caption text-medium-emphasis">Kassenstand</div>
              <div class="text-h6 font-weight-bold" :class="fund.fund_balance_cents >= 0 ? 'text-success' : 'text-error'">
                {{ eur(fund.fund_balance_cents) }}
              </div>
            </v-col>
          </v-row>
        </v-card-text>

        <!-- Kostenaufstellung -->
        <v-divider />
        <v-expansion-panels variant="accordion" flat>
          <v-expansion-panel>
            <v-expansion-panel-title>
              <v-icon icon="mdi-calculator" size="small" class="mr-2" />
              <span class="text-body-2">Aufschlüsselung {{ selectedYear }}</span>
            </v-expansion-panel-title>
            <v-expansion-panel-text>
              <!-- Laufende Kosten -->
              <div class="text-subtitle-2 font-weight-bold mb-2">
                <v-icon icon="mdi-repeat" size="small" class="mr-1" />
                Laufende Kosten
              </div>
              <div v-if="recurring.length === 0" class="text-body-2 text-grey mb-3">Keine laufenden Kosten.</div>
              <v-table v-else density="compact" class="mb-3">
                <thead>
                  <tr>
                    <th>Posten</th>
                    <th class="text-right">Betrag</th>
                    <th class="text-right">Pro Monat</th>
                    <th class="text-right">Pro Jahr</th>
                    <th v-if="auth.isAdmin" style="width: 80px"></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="recurring.filter(r => r.interval === 'monthly').length" class="bg-grey-lighten-5">
                    <td colspan="5" class="text-caption font-weight-bold text-medium-emphasis py-1">Monatliche Kosten</td>
                  </tr>
                  <tr v-for="r in recurring.filter(r => r.interval === 'monthly')" :key="'m-' + r.id">
                    <td>
                      {{ r.description }}
                      <span v-if="r.notes" class="text-caption text-medium-emphasis ml-1">({{ r.notes }})</span>
                      <div class="text-caption text-medium-emphasis">
                        {{ new Date(r.valid_from).toLocaleDateString('de-DE') }}
                        {{ r.valid_to ? '– ' + new Date(r.valid_to).toLocaleDateString('de-DE') : '– unbegrenzt' }}
                      </div>
                    </td>
                    <td class="text-right text-medium-emphasis">{{ eur(r.amount_cents) }} / Monat</td>
                    <td class="text-right font-weight-bold">{{ eur(r.amount_cents) }}</td>
                    <td class="text-right">{{ eur(r.amount_cents * 12) }}</td>
                    <td v-if="auth.isAdmin" class="text-right">
                      <v-btn size="x-small" icon="mdi-pencil" variant="text" density="compact" @click="openEditRecurringDialog(r)" />
                      <v-btn size="x-small" icon="mdi-delete" variant="text" color="error" density="compact" @click="deleteRecurring(r.id)" />
                    </td>
                  </tr>
                  <tr v-if="recurring.filter(r => r.interval === 'monthly').length" class="bg-grey-lighten-4">
                    <td class="font-weight-bold" colspan="2">Σ Monatliche Kosten</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_recurring_monthly_cents) }}</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_recurring_monthly_cents * 12) }}</td>
                    <td v-if="auth.isAdmin"></td>
                  </tr>
                  <tr v-if="recurring.filter(r => r.interval === 'yearly').length" class="bg-grey-lighten-5">
                    <td colspan="5" class="text-caption font-weight-bold text-medium-emphasis py-1">Jährliche Kosten</td>
                  </tr>
                  <tr v-for="r in recurring.filter(r => r.interval === 'yearly')" :key="'y-' + r.id">
                    <td>
                      {{ r.description }}
                      <span v-if="r.notes" class="text-caption text-medium-emphasis ml-1">({{ r.notes }})</span>
                      <div class="text-caption text-medium-emphasis">
                        {{ new Date(r.valid_from).toLocaleDateString('de-DE') }}
                        {{ r.valid_to ? '– ' + new Date(r.valid_to).toLocaleDateString('de-DE') : '– unbegrenzt' }}
                      </div>
                    </td>
                    <td class="text-right text-medium-emphasis">{{ eur(r.amount_cents) }} / Jahr</td>
                    <td class="text-right">{{ eur(Math.round(r.amount_cents / 12)) }}</td>
                    <td class="text-right font-weight-bold">{{ eur(r.amount_cents) }}</td>
                    <td v-if="auth.isAdmin" class="text-right">
                      <v-btn size="x-small" icon="mdi-pencil" variant="text" density="compact" @click="openEditRecurringDialog(r)" />
                      <v-btn size="x-small" icon="mdi-delete" variant="text" color="error" density="compact" @click="deleteRecurring(r.id)" />
                    </td>
                  </tr>
                  <tr v-if="recurring.filter(r => r.interval === 'yearly').length" class="bg-grey-lighten-4">
                    <td class="font-weight-bold" colspan="2">Σ Jährliche Kosten</td>
                    <td class="text-right font-weight-bold">{{ eur(Math.round(fund.total_recurring_yearly_cents / 12)) }}</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_recurring_yearly_cents) }}</td>
                    <td v-if="auth.isAdmin"></td>
                  </tr>
                  <tr><td colspan="5" class="pa-1"></td></tr>
                  <tr class="bg-primary-lighten-5">
                    <td class="font-weight-bold text-primary" colspan="2">Σ Alle laufenden Kosten</td>
                    <td class="text-right font-weight-bold text-primary">{{ eur(Math.round(fund.total_recurring_annual_cents / 12)) }}</td>
                    <td class="text-right font-weight-bold text-primary">{{ eur(fund.total_recurring_annual_cents) }}</td>
                    <td v-if="auth.isAdmin"></td>
                  </tr>
                </tbody>
              </v-table>

              <!-- Einzelposten -->
              <div class="text-subtitle-2 font-weight-bold mb-2">
                <v-icon icon="mdi-receipt" size="small" class="mr-1" />
                Einzelposten ({{ selectedYear }})
              </div>
              <div v-if="fund.total_onetime_expenses_cents === 0" class="text-body-2 text-grey mb-3">Keine Einzelposten.</div>
              <v-table v-else density="compact" class="mb-3">
                <thead><tr><th>Datum</th><th>Posten</th><th>Von</th><th class="text-right">Betrag</th></tr></thead>
                <tbody>
		  <tr v-for="e in expenses.filter(x => x.is_shared && x.confirmed_by_admin)" :key="'calc-e-' + e.id">
                    <td>{{ new Date(e.expense_date).toLocaleDateString('de-DE') }}</td>
                    <td>{{ e.description }}
                      <v-chip v-if="e.category" size="x-small" class="ml-1" variant="tonal">{{ e.category.icon || '' }} {{ e.category.name }}</v-chip>
	  	        <v-chip v-if="e.is_shared && !e.confirmed_by_admin && e.user.id !== auth.user?.id" size="x-small" color="warning" variant="flat" class="ml-1">
			  ⏳ Bestätigung ausstehend
			</v-chip>
			<v-chip v-if="e.is_shared && e.confirmed_by_admin" size="x-small" color="success" variant="flat" class="ml-1">
			  ✓ Bestätigt
			</v-chip>

                    </td>
                    <td>{{ e.user.display_name }}</td>
                    <td class="text-right font-weight-bold">{{ eur(e.amount_cents) }}
			  <v-btn
			    v-if="auth.isAdmin && e.is_shared && !e.confirmed_by_admin"
			    size="x-small"
			    color="success"
			    variant="tonal"
			    class="mr-1"
			    @click.stop="confirmExpense(e.id)"
			  >
			    ✓ Bestätigen
			  </v-btn>

                      <v-btn v-if="auth.isAdmin" size="x-small" icon="mdi-delete" variant="text" color="error" density="compact" class="ml-1" @click="deleteExpense(e.id)" />
                    </td>
                  </tr>
		  <tr v-for="e in expenses.filter(x => x.is_shared && !x.confirmed_by_admin)" :key="'calc-pending-' + e.id" class="text-medium-emphasis">
                    <td>{{ new Date(e.expense_date).toLocaleDateString('de-DE') }}</td>
                    <td>
                      {{ e.description }}
                      <v-chip size="x-small" color="warning" variant="flat" class="ml-1">⏳ unbestätigt</v-chip>
                    </td>
                    <td>{{ e.user.display_name }}</td>
                    <td class="text-right">
                      {{ eur(e.amount_cents) }}
                      <v-btn v-if="auth.isAdmin" size="x-small" color="success" variant="tonal" density="compact" class="ml-1" @click="confirmExpense(e.id)">✓</v-btn>
                    </td>
                  </tr>
                  <tr class="bg-grey-lighten-4">
                    <td class="font-weight-bold" colspan="3">Σ Einmal-Ausgaben (umgelegt)</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_onetime_expenses_cents) }}</td>
                  </tr>
                </tbody>
              </v-table>

              <!-- Gesamtrechnung -->
              <v-divider class="mb-3" />
              <div class="text-subtitle-2 font-weight-bold mb-2">
                <v-icon icon="mdi-sigma" size="small" class="mr-1" />
                Gesamtrechnung {{ selectedYear }}
              </div>
              <v-table density="compact">
                <tbody>
                  <tr>
                    <td>Laufende Kosten / Jahr</td>
                    <td class="text-right">{{ eur(fund.total_recurring_annual_cents) }}</td>
                    <td class="text-right text-medium-emphasis">pro Person: {{ eur(fund.share_recurring_per_member_annual_cents) }}</td>
                  </tr>
                  <tr>
                    <td>+ Einmal-Ausgaben</td>
                    <td class="text-right">{{ eur(fund.total_onetime_expenses_cents) }}</td>
                    <td class="text-right text-medium-emphasis">pro Person: {{ eur(fund.share_onetime_per_member_cents) }}</td>
                  </tr>
                  <tr class="bg-grey-lighten-4">
                    <td class="font-weight-bold">= Gesamtkosten</td>
                    <td class="text-right font-weight-bold">{{ eur(fund.total_costs_annual_cents) }}</td>
                    <td class="text-right font-weight-bold">pro Person: {{ eur(fund.share_total_per_member_annual_cents) }}</td>
                  </tr>
                  <tr><td colspan="3" class="pa-1"></td></tr>
                  <tr class="bg-primary-lighten-5">
                    <td class="font-weight-bold text-primary" colspan="2">Grundbeitrag (laufend)</td>
                    <td class="text-right font-weight-bold text-primary text-h6">{{ eur(fund.share_recurring_per_member_monthly_cents) }} / Monat</td>
                  </tr>
                  <tr class="bg-primary-lighten-5">
                    <td class="font-weight-bold text-primary" colspan="2">Gesamt-Soll / Person / Jahr</td>
                    <td class="text-right font-weight-bold text-primary text-h6">{{ eur(fund.share_total_per_member_annual_cents) }}</td>
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
          <v-chip v-for="b in fund.member_balances" :key="b.user_id" :color="balanceColor(b.remaining_cents)"
            variant="tonal" class="mr-2 mb-1" size="small">
            {{ b.display_name }}:
            <strong class="ml-1">{{ b.remaining_cents > 0 ? '-' : '+' }}{{ eur(Math.abs(b.remaining_cents)) }}</strong>
            <span v-if="b.total_standing_order_cents > 0" class="ml-1 text-caption">(DA: {{ eur(b.total_standing_order_cents) }})</span>
          </v-chip>
        </v-card-text>
      </v-card>

      <!-- ═══ Quick Action Buttons ═════════════════════════════ -->
      <div class="d-flex ga-2 mb-4 flex-wrap">
        <v-btn color="primary" size="large" prepend-icon="mdi-plus" @click="openExpenseDialog">Ausgabe</v-btn>
        <v-btn color="success" size="large" variant="tonal" prepend-icon="mdi-cash-plus" @click="openPaymentDialog">Einzahlung</v-btn>
        <v-btn color="info" variant="tonal" prepend-icon="mdi-bank-transfer" @click="openStandingDialog">Dauerauftrag</v-btn>
        <v-btn v-if="auth.isAdmin" color="default" variant="outlined" size="small" prepend-icon="mdi-repeat" @click="openRecurringDialog">Laufende Kosten</v-btn>
      </div>

      <!-- ═══ Tabs ═════════════════════════════════════════════ -->
      <v-tabs v-model="tab" color="primary" class="mb-4">
        <v-tab value="expenses"><v-icon start icon="mdi-receipt" />Ausgaben ({{ expenses.length }})</v-tab>
        <v-tab value="payments"><v-icon start icon="mdi-cash-multiple" />Einzahlungen ({{ payments.length }})</v-tab>
        <v-tab value="standing"><v-icon start icon="mdi-bank-transfer" />Daueraufträge ({{ standingOrders.length }})</v-tab>
        <v-tab value="recurring"><v-icon start icon="mdi-repeat" />Laufend ({{ recurring.length }})</v-tab>
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
                <v-avatar v-if="e.receipt_image_path" rounded="lg" size="48">
                  <v-img :src="`/api/finance/receipts/${e.receipt_image_path.replace('receipts/', '')}`" cover />
                </v-avatar>
                <v-avatar v-else color="primary" variant="tonal" size="48"><v-icon icon="mdi-receipt" /></v-avatar>
              </template>
              <template #title>
                <span class="font-weight-bold">{{ e.description }}</span>
                <v-chip v-if="e.category" size="x-small" class="ml-2" variant="tonal">{{ e.category.icon || '' }} {{ e.category.name }}</v-chip>
                <v-chip v-if="!e.is_shared" size="x-small" class="ml-1" color="warning" variant="flat">nicht umgelegt</v-chip>
              </template>
              <template #subtitle>
                {{ new Date(e.expense_date).toLocaleDateString('de-DE') }} · {{ e.user.display_name }}
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
                <v-avatar v-if="p.receipt_image_path" rounded="lg" size="48">
                  <v-img :src="`/api/finance/receipts/${p.receipt_image_path.replace('receipts/', '')}`" cover />
                </v-avatar>
                <v-avatar v-else color="success" variant="tonal" size="48"><v-icon icon="mdi-cash-plus" /></v-avatar>
              </template>
              <template #title>
                <span class="font-weight-bold">{{ p.for_user ? p.for_user.display_name : p.user.display_name }}</span>
                <v-chip v-if="p.for_user && p.for_user.id !== p.user.id" size="x-small" class="ml-1" variant="tonal">
                  eingetragen von {{ p.user.display_name }}
                </v-chip>
                <v-chip size="x-small" class="ml-2" variant="tonal">{{ paymentTypeLabel(p.payment_type) }}</v-chip>
                <v-chip v-if="p.confirmed_by_admin" size="x-small" color="success" variant="flat" class="ml-1">✓ Bestätigt</v-chip>
              </template>
              <template #subtitle>
                {{ new Date(p.payment_date).toLocaleDateString('de-DE') }}
                <span v-if="p.description"> · {{ p.description }}</span>
              </template>
              <template #append>
                <div class="text-right">
                  <div class="text-body-1 font-weight-bold text-success">{{ eur(p.amount_cents) }}</div>
                  <div class="d-flex ga-1 justify-end mt-1">
                    <v-btn v-if="auth.isAdmin && !p.confirmed_by_admin" size="x-small" color="success" variant="tonal" @click="confirmPayment(p.id)">Bestätigen</v-btn>
                    <v-btn v-if="auth.isAdmin" size="x-small" icon="mdi-delete" variant="text" color="error" @click="deletePayment(p.id)" />
                  </div>
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-window-item>

        <!-- ─── Standing Orders Tab ──────────────────────────── -->
        <v-window-item value="standing">
          <div v-if="standingOrders.length === 0" class="text-center py-8">
            <v-icon icon="mdi-bank-transfer-out" size="64" color="grey" />
            <p class="text-body-1 text-grey mt-2">Keine Daueraufträge eingerichtet</p>
            <v-btn color="info" variant="tonal" class="mt-2" @click="openStandingDialog">Dauerauftrag anlegen</v-btn>
          </div>

          <v-card v-for="order in standingOrders" :key="order.id" class="mb-4">
            <v-card-title class="d-flex align-center">
              <v-icon icon="mdi-bank-transfer" class="mr-2" color="info" />
              <span class="font-weight-bold">{{ order.user.display_name }}</span>
              <span class="text-h6 font-weight-bold text-info ml-2">{{ eur(order.amount_cents) }} / Monat</span>
              <v-spacer />
              <v-btn v-if="auth.isAdmin || order.user.id === auth.user?.id" size="small" icon="mdi-pencil" variant="text" @click="openEditStandingDialog(order)" />
              <v-btn v-if="auth.isAdmin" size="small" icon="mdi-delete" variant="text" color="error" @click="deleteStanding(order.id)" />
            </v-card-title>

            <v-card-subtitle>
              {{ new Date(order.valid_from).toLocaleDateString('de-DE') }}
              {{ order.valid_to ? '– ' + new Date(order.valid_to).toLocaleDateString('de-DE') : '– unbegrenzt' }}
              <span v-if="order.description"> · {{ order.description }}</span>
            </v-card-subtitle>

            <!-- Month grid -->
            <v-card-text>
              <div class="d-flex flex-wrap ga-1">
                <template v-for="month in 12" :key="month">
                  <v-chip
                    v-if="orderActiveInMonth(order, month)"
                    :color="isMonthSkipped(order, month) ? 'error' : 'success'"
                    :variant="isMonthSkipped(order, month) ? 'flat' : 'tonal'"
                    size="small"
                    :style="{ cursor: auth.isAdmin ? 'pointer' : 'default' }"
                    @click="auth.isAdmin && (isMonthSkipped(order, month) ? removeSkip(order.id, getSkipId(order, month)!) : openSkipDialog(order))"
                  >
                    {{ monthNames[month - 1] }}
                    <v-icon v-if="isMonthSkipped(order, month)" end icon="mdi-close" size="x-small" />
                    <v-icon v-else end icon="mdi-check" size="x-small" />
                  </v-chip>
                  <v-chip v-else size="small" variant="outlined" color="grey" disabled>
                    {{ monthNames[month - 1] }}
                  </v-chip>
                </template>
              </div>
              <div class="text-caption text-medium-emphasis mt-2">
                Grün = gezahlt · Rot = nicht gezahlt
                <span v-if="auth.isAdmin"> · Klicken zum Umschalten</span>
              </div>
            </v-card-text>
          </v-card>
        </v-window-item>

        <!-- ─── Recurring Costs Tab ──────────────────────────── -->
        <v-window-item value="recurring">
          <div v-if="recurring.length === 0" class="text-center py-8">
            <v-icon icon="mdi-repeat-off" size="64" color="grey" />
            <p class="text-body-1 text-grey mt-2">Keine laufenden Kosten</p>
            <v-btn v-if="auth.isAdmin" color="primary" variant="tonal" class="mt-2" @click="openRecurringDialog">Erste laufende Kosten anlegen</v-btn>
          </div>
          <v-list v-else>
            <v-list-item v-for="r in recurring" :key="r.id">
              <template #prepend><v-avatar color="warning" variant="tonal"><v-icon icon="mdi-repeat" /></v-avatar></template>
              <template #title>
                <span class="font-weight-bold">{{ r.description }}</span>
              </template>
              <template #subtitle>
                {{ intervalLabel(r.interval) }} · {{ eur(r.amount_cents) }}
                <br />
                {{ new Date(r.valid_from).toLocaleDateString('de-DE') }}
                {{ r.valid_to ? '– ' + new Date(r.valid_to).toLocaleDateString('de-DE') : '– unbegrenzt' }}
                <span v-if="r.notes"> · {{ r.notes }}</span>
              </template>
              <template #append>
                <div class="text-right">
                  <div class="text-body-1 font-weight-bold">{{ eur(r.amount_cents) }}</div>
                  <div class="text-caption text-medium-emphasis">
                    {{ r.interval === 'monthly' ? eur(r.amount_cents * 12) + '/Jahr' : eur(r.amount_cents) + '/Jahr' }}
                  </div>
                  <div v-if="auth.isAdmin" class="d-flex ga-1 justify-end mt-1">
                    <v-btn size="x-small" icon="mdi-pencil" variant="text" @click="openEditRecurringDialog(r)" />
                    <v-btn size="x-small" icon="mdi-delete" variant="text" color="error" @click="deleteRecurring(r.id)" />
                  </div>
                </div>
              </template>
            </v-list-item>
          </v-list>
        </v-window-item>
      </v-window>
    </template>

    <!-- ═══ Expense Dialog ═════════════════════════════════════ -->
    <v-dialog v-model="showExpenseDialog" max-width="500" eager>
      <v-card>
        <v-card-title><v-icon icon="mdi-receipt" class="mr-2" />Ausgabe erfassen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveExpense">
            <v-text-field v-model.number="expenseForm.amount" label="Betrag (€) *" type="number" min="0.01" step="0.01" prefix="€" autofocus inputmode="decimal" variant="outlined" density="comfortable" class="mb-3 text-h5" />
            <v-text-field v-model="expenseForm.description" label="Wofür? *" placeholder="z.B. Baumarkt Erde 20L" variant="outlined" density="comfortable" class="mb-3" />
            <v-combobox v-model="expenseForm.category_name" label="Kategorie" :items="categoryNames" placeholder="Tippen oder wählen..." clearable variant="outlined" density="comfortable" class="mb-3" hint="Neue Kategorie? Einfach eintippen!" persistent-hint />
            <v-text-field v-model="expenseForm.expense_date" label="Datum" type="date" variant="outlined" density="comfortable" class="mb-3" />
            <v-checkbox v-model="expenseForm.is_shared" label="Auf alle Mitglieder umlegen" hint="Wenn deaktiviert, wird dieser Posten nicht in die Jahreskosten eingerechnet" persistent-hint color="primary" class="mb-3" />
            <div class="text-body-2 text-medium-emphasis mb-1">Kassenbon / Rechnung:</div>
            <PhotoCapture v-model="expenseForm.receipt_image_path" label="Beleg fotografieren" />
            <v-textarea v-model="expenseForm.notes" label="Notizen" rows="2" variant="outlined" density="comfortable" class="mt-3" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showExpenseDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" size="large" :disabled="!expenseForm.amount || !expenseForm.description" @click="saveExpense"><v-icon start icon="mdi-check" />Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Payment Dialog ═════════════════════════════════════ -->
    <v-dialog v-model="showPaymentDialog" max-width="500" eager>
      <v-card>
        <v-card-title><v-icon icon="mdi-cash-plus" class="mr-2" color="success" />Einzahlung in die Gartenkasse</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="savePayment">
            <v-text-field v-model.number="paymentForm.amount" label="Betrag (€) *" type="number" min="0.01" step="0.01" prefix="€" autofocus inputmode="decimal" variant="outlined" density="comfortable" class="mb-3 text-h5" />
            <v-select v-if="auth.isAdmin" v-model="paymentForm.for_user_id" label="Einzahlung für" :items="users" item-title="display_name" item-value="id" clearable variant="outlined" density="comfortable" class="mb-3" hint="Leer = für dich selbst" persistent-hint />
            <v-btn-toggle v-model="paymentForm.payment_type" mandatory color="primary" class="mb-3" density="comfortable">
              <v-btn value="cash">💵 Bar</v-btn>
              <v-btn value="transfer">🏦 Überweisung</v-btn>
              <v-btn value="material">🛒 Sachleistung</v-btn>
            </v-btn-toggle>
            <v-text-field v-model="paymentForm.payment_date" label="Datum" type="date" variant="outlined" density="comfortable" class="mb-3" />
            <v-text-field v-model="paymentForm.description" label="Beschreibung" :placeholder="paymentForm.payment_type === 'material' ? 'z.B. Erde mitgebracht' : 'optional'" variant="outlined" density="comfortable" class="mb-3" />
            <template v-if="paymentForm.payment_type === 'material'">
              <div class="text-body-2 text-medium-emphasis mb-1">Beleg / Rechnung:</div>
              <PhotoCapture v-model="paymentForm.receipt_image_path" label="Beleg fotografieren" />
            </template>
            <v-alert v-if="myBalance && myBalance.remaining_cents > 0" type="info" variant="tonal" density="compact" class="mt-3">
              Du schuldest noch {{ eur(myBalance.remaining_cents) }} für {{ selectedYear }}.
            </v-alert>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showPaymentDialog = false">Abbrechen</v-btn>
          <v-btn color="success" size="large" :disabled="!paymentForm.amount" @click="savePayment"><v-icon start icon="mdi-check" />Einzahlen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Recurring Cost Dialog (New) ════════════════════════ -->
    <v-dialog v-model="showRecurringDialog" max-width="500">
      <v-card>
        <v-card-title>Laufende Kosten anlegen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveRecurring">
            <v-text-field v-model="recurringForm.description" label="Beschreibung *" placeholder="z.B. Strom, Pacht, Wasser" autofocus variant="outlined" density="comfortable" class="mb-3" />
            <v-text-field v-model.number="recurringForm.amount" label="Betrag (€) *" type="number" min="0.01" step="0.01" prefix="€" inputmode="decimal" variant="outlined" density="comfortable" class="mb-3" />
            <v-btn-toggle v-model="recurringForm.interval" mandatory color="primary" class="mb-3" density="comfortable">
              <v-btn value="monthly">Monatlich</v-btn>
              <v-btn value="yearly">Jährlich</v-btn>
            </v-btn-toggle>
            <v-row dense class="mb-3">
              <v-col cols="6"><v-text-field v-model="recurringForm.valid_from" label="Gültig ab *" type="date" variant="outlined" density="comfortable" /></v-col>
              <v-col cols="6"><v-text-field v-model="recurringForm.valid_to" label="Gültig bis" type="date" variant="outlined" density="comfortable" hint="Leer = unbegrenzt" persistent-hint /></v-col>
            </v-row>
            <v-textarea v-model="recurringForm.notes" label="Notizen" rows="2" variant="outlined" density="comfortable" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showRecurringDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!recurringForm.amount || !recurringForm.description" @click="saveRecurring">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Recurring Cost Dialog (Edit) ═══════════════════════ -->
    <v-dialog v-model="showEditRecurringDialog" max-width="500">
      <v-card>
        <v-card-title>Laufende Kosten bearbeiten</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEditRecurring">
            <v-text-field v-model="editRecurringForm.description" label="Beschreibung *" variant="outlined" density="comfortable" class="mb-3" />
            <v-text-field v-model.number="editRecurringForm.amount" label="Betrag (€) *" type="number" min="0.01" step="0.01" prefix="€" inputmode="decimal" variant="outlined" density="comfortable" class="mb-3" />
            <v-btn-toggle v-model="editRecurringForm.interval" mandatory color="primary" class="mb-3" density="comfortable">
              <v-btn value="monthly">Monatlich</v-btn>
              <v-btn value="yearly">Jährlich</v-btn>
            </v-btn-toggle>
            <v-row dense class="mb-3">
              <v-col cols="6"><v-text-field v-model="editRecurringForm.valid_from" label="Gültig ab *" type="date" variant="outlined" density="comfortable" /></v-col>
              <v-col cols="6"><v-text-field v-model="editRecurringForm.valid_to" label="Gültig bis" type="date" variant="outlined" density="comfortable" hint="Leer = unbegrenzt" persistent-hint /></v-col>
            </v-row>
            <v-textarea v-model="editRecurringForm.notes" label="Notizen" rows="2" variant="outlined" density="comfortable" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showEditRecurringDialog = false">Abbrechen</v-btn>
          <v-btn color="primary" :disabled="!editRecurringForm.amount || !editRecurringForm.description" @click="saveEditRecurring">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Standing Order Dialog (New) ════════════════════════ -->
    <v-dialog v-model="showStandingDialog" max-width="500">
      <v-card>
        <v-card-title><v-icon icon="mdi-bank-transfer" class="mr-2" color="info" />Dauerauftrag anlegen</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveStanding">
            <v-text-field v-model.number="standingForm.amount" label="Betrag pro Monat (€) *" type="number" min="0.01" step="0.01" prefix="€" autofocus inputmode="decimal" variant="outlined" density="comfortable" class="mb-3 text-h5" />
            <v-select v-if="auth.isAdmin" v-model="standingForm.user_id" label="Für wen?" :items="users" item-title="display_name" item-value="id" clearable variant="outlined" density="comfortable" class="mb-3" hint="Leer = für dich selbst" persistent-hint />
            <v-text-field v-model="standingForm.description" label="Beschreibung" placeholder="z.B. SEPA Lastschrift" variant="outlined" density="comfortable" class="mb-3" />
            <v-row dense class="mb-3">
              <v-col cols="6"><v-text-field v-model="standingForm.valid_from" label="Ab wann *" type="date" variant="outlined" density="comfortable" /></v-col>
              <v-col cols="6"><v-text-field v-model="standingForm.valid_to" label="Bis wann" type="date" variant="outlined" density="comfortable" hint="Leer = unbegrenzt" persistent-hint /></v-col>
            </v-row>
            <v-textarea v-model="standingForm.notes" label="Notizen" rows="2" variant="outlined" density="comfortable" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showStandingDialog = false">Abbrechen</v-btn>
          <v-btn color="info" :disabled="!standingForm.amount" @click="saveStanding">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Standing Order Dialog (Edit) ═══════════════════════ -->
    <v-dialog v-model="showEditStandingDialog" max-width="500">
      <v-card>
        <v-card-title>Dauerauftrag bearbeiten</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="saveEditStanding">
            <v-text-field v-model.number="editStandingForm.amount" label="Betrag pro Monat (€) *" type="number" min="0.01" step="0.01" prefix="€" inputmode="decimal" variant="outlined" density="comfortable" class="mb-3" />
            <v-text-field v-model="editStandingForm.description" label="Beschreibung" variant="outlined" density="comfortable" class="mb-3" />
            <v-row dense class="mb-3">
              <v-col cols="6"><v-text-field v-model="editStandingForm.valid_from" label="Ab wann *" type="date" variant="outlined" density="comfortable" /></v-col>
              <v-col cols="6"><v-text-field v-model="editStandingForm.valid_to" label="Bis wann" type="date" variant="outlined" density="comfortable" hint="Leer = unbegrenzt" persistent-hint /></v-col>
            </v-row>
            <v-textarea v-model="editStandingForm.notes" label="Notizen" rows="2" variant="outlined" density="comfortable" />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showEditStandingDialog = false">Abbrechen</v-btn>
          <v-btn color="info" :disabled="!editStandingForm.amount" @click="saveEditStanding">Speichern</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Skip Month Dialog ══════════════════════════════════ -->
    <v-dialog v-model="showSkipDialog" max-width="400">
      <v-card>
        <v-card-title class="text-error"><v-icon icon="mdi-close-circle" class="mr-2" />Nicht gezahlt markieren</v-card-title>
        <v-card-text>
          <p class="mb-3">{{ skipForm.order_description }}</p>
          <v-select v-model="skipForm.month" label="Monat" :items="monthNames.map((n, i) => ({ title: n, value: i + 1 }))" variant="outlined" density="comfortable" class="mb-3" />
          <v-text-field v-model.number="skipForm.year" label="Jahr" type="number" variant="outlined" density="comfortable" class="mb-3" />
          <v-text-field v-model="skipForm.reason" label="Grund (optional)" placeholder="z.B. Lastschrift fehlgeschlagen" variant="outlined" density="comfortable" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showSkipDialog = false">Abbrechen</v-btn>
          <v-btn color="error" @click="saveSkip">Nicht gezahlt</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>
