<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface MemberBalance {
  user_id: number;
  display_name: string;
  total_paid_cents: number;
  total_standing_order_cents: number;
  total_standing_order_projected_cents: number;
  total_income_cents: number;
  total_income_projected_cents: number;
  share_recurring_cents: number;
  share_onetime_cents: number;
  share_total_cents: number;
  remaining_cents: number;
  remaining_projected_cents: number;
  duty_compensation_cents: number;
}

interface FundOverview {
  total_recurring_monthly_cents: number;
  total_recurring_annual_cents: number;
  total_onetime_expenses_cents: number;
  total_costs_annual_cents: number;
  total_income_cents: number;
  total_income_projected_cents: number;
  fund_balance_cents: number;
  share_recurring_per_member_monthly_cents: number;
  share_recurring_per_member_annual_cents: number;
  share_total_per_member_annual_cents: number;
  share_total_per_member_monthly_cents: number;
  member_count: number;
  member_balances: MemberBalance[];
}

interface DutyBalance {
  user_id: number;
  display_name: string;
  assigned_hours: number;
  confirmed_hours: number;
  pending_hours: number;
  remaining_hours: number;
  compensation_cents: number;
}

interface DutyOverview {
  year: number;
  total_hours: number;
  hourly_rate_cents: number;
  member_balances: DutyBalance[];
}

const fund = ref<FundOverview | null>(null);
const duty = ref<DutyOverview | null>(null);
const loading = ref(true);

const myBalance = computed(() => {
  if (!fund.value || !auth.user) return null;
  return fund.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
});

const myDuty = computed(() => {
  if (!duty.value?.member_balances || !auth.user) return null;
  return duty.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
});

const monthsRemaining = computed(() => {
  const now = new Date();
  // Remaining full months including current month
  return Math.max(12 - now.getMonth(), 1);  // getMonth() is 0-based, so Jan=0
});

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

function dutyCardColor(remaining: number): string {
  if (remaining <= 0) return "success";
  return "warning";
}

onMounted(async () => {
  try {
    const currentYear = new Date().getFullYear();
    const [fundData, dutyData] = await Promise.all([
      api.get<FundOverview>("/finance/fund/"),
      api.get<DutyOverview>(`/duty/overview/${currentYear}`).catch(() => null),
    ]);

    fund.value = fundData;
    duty.value = dutyData;
  } catch {
    // Silently fail
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div>
    <h1 class="text-h4 mb-6">
      Hallo, {{ auth.displayName }}! 👋
    </h1>

    <!-- ═══ My Finance Status ══════════════════════════════════ -->
    <v-card
      v-if="myBalance"
      :color="balanceColor(myBalance.remaining_cents)"
      variant="tonal"
      class="mb-6"
      to="/finance"
    >
      <v-card-text class="d-flex align-center pa-4">
        <div class="flex-grow-1">
          <div class="text-body-2 text-medium-emphasis">Dein Kassenstand {{ new Date().getFullYear() }}</div>
          <div class="text-h4 font-weight-bold my-1">
            {{ eur(Math.abs(myBalance.remaining_cents)) }}
          </div>
          <div class="text-body-2">{{ balanceText(myBalance.remaining_cents) }}</div>
          <div class="text-caption mt-1">
            Soll: {{ eur(myBalance.share_total_cents) }}
            · Bezahlt: {{ eur(myBalance.total_paid_cents) }}
            · Daueraufträge: {{ eur(myBalance.total_standing_order_cents) }}
          </div>
          <div v-if="myBalance.duty_compensation_cents > 0" class="text-caption">
            + {{ eur(myBalance.duty_compensation_cents) }} Ausgleich Gartenstunden
          </div>
        </div>
        <div class="text-right">
          <v-icon icon="mdi-cash-register" size="48" class="mb-2" />
          <div class="text-caption">
            {{ eur(fund!.share_recurring_per_member_monthly_cents) }} / Monat
          </div>
        </div>
      </v-card-text>

      <!-- ─── Prognose & Empfehlung ─────────────────────────── -->
      <v-divider />
      <v-card-text class="pa-4 pt-3">
        <div class="text-body-2 font-weight-bold mb-2">
          <v-icon icon="mdi-crystal-ball" size="small" class="mr-1" />
          Prognose Ende {{ new Date().getFullYear() }}
        </div>

        <!-- Prognose: alles gedeckt -->
        <template v-if="myBalance.remaining_projected_cents <= 0">
          <v-chip color="success" variant="flat" size="small" class="mr-2">
            <v-icon icon="mdi-check-circle" start size="small" />
            Alles gedeckt!
          </v-chip>
          <span v-if="myBalance.remaining_projected_cents < 0" class="text-body-2">
            {{ eur(Math.abs(myBalance.remaining_projected_cents)) }} Guthaben erwartet
          </span>
        </template>

        <!-- Prognose: noch offen -->
        <template v-else>
          <v-chip color="error" variant="tonal" size="small" class="mr-2 mb-2">
            <v-icon icon="mdi-alert" start size="small" />
            {{ eur(myBalance.remaining_projected_cents) }} offen Ende Jahr
          </v-chip>

          <div class="text-body-2 mt-1">
            <v-icon icon="mdi-lightbulb-outline" size="small" class="mr-1" />
            <strong>Empfehlung:</strong>
            Erhöhe deinen monatlichen Abschlag um
            <strong>{{ eur(Math.ceil(myBalance.remaining_projected_cents / monthsRemaining / 100) * 100) }}</strong>,
            oder zahle einmalig
            <strong>{{ eur(myBalance.remaining_projected_cents) }}</strong> ein.
          </div>
        </template>
      </v-card-text>
    </v-card>

    <!-- ═══ My Duty Status ═════════════════════════════════════ -->
    <v-card
      v-if="myDuty && duty"
      :color="dutyCardColor(myDuty.remaining_hours)"
      variant="tonal"
      class="mb-6"
      to="/duty"
    >
      <v-card-text class="d-flex align-center pa-4">
        <div class="flex-grow-1">
          <div class="text-body-2 text-medium-emphasis">Deine Gartenstunden {{ duty.year }}</div>

          <!-- Fertig oder Überstunden -->
          <template v-if="myDuty.remaining_hours <= 0">
            <div class="text-h4 font-weight-bold my-1">
              Erledigt! 🎉
            </div>
            <div class="text-body-2">
              {{ myDuty.confirmed_hours + myDuty.pending_hours }} von {{ myDuty.assigned_hours }} Stunden geleistet
              <span v-if="myDuty.remaining_hours < 0">
                · {{ Math.abs(myDuty.remaining_hours) }}h extra
              </span>
            </div>
          </template>

          <!-- Noch offen -->
          <template v-else>
            <div class="text-h4 font-weight-bold my-1">
              {{ myDuty.remaining_hours }}h offen
            </div>
            <div class="text-body-2">
              {{ myDuty.confirmed_hours + myDuty.pending_hours }} von {{ myDuty.assigned_hours }} Stunden geleistet
            </div>
            <div v-if="myDuty.compensation_cents > 0" class="text-caption mt-1">
              Alternativ: {{ eur(myDuty.compensation_cents) }} Ausgleich
              ({{ eur(duty.hourly_rate_cents) }}/h)
            </div>
          </template>
        </div>
        <div class="text-right">
          <v-icon icon="mdi-shovel" size="48" class="mb-2" />
          <div class="text-caption">
            {{ myDuty.confirmed_hours }}h bestätigt
          </div>
          <div v-if="myDuty.pending_hours > 0" class="text-caption">
            {{ myDuty.pending_hours }}h ausstehend
          </div>
        </div>
      </v-card-text>

      <!-- Progress Bar -->
      <v-progress-linear
        :model-value="Math.min(((myDuty.confirmed_hours + myDuty.pending_hours) / myDuty.assigned_hours) * 100, 100)"
        :color="myDuty.remaining_hours <= 0 ? 'success' : 'warning'"
        height="6"
      />
    </v-card>

    <!-- ═══ All Members Overview ═══════════════════════════════ -->
    <v-card v-if="fund" class="mt-6">
      <v-card-title class="d-flex align-center">
        <v-icon icon="mdi-account-group" class="mr-2" />
        Kassenübersicht
      </v-card-title>
      <v-card-text>
        <v-row dense class="mb-4">
          <v-col cols="6" sm="4">
            <div class="text-caption text-medium-emphasis">Jahreskosten</div>
            <div class="text-h6 font-weight-bold">{{ eur(fund.total_costs_annual_cents) }}</div>
          </v-col>
          <v-col cols="6" sm="4">
            <div class="text-caption text-medium-emphasis">Eingegangen</div>
            <div class="text-h6 font-weight-bold text-success">{{ eur(fund.total_income_cents) }}</div>
          </v-col>
          <v-col cols="12" sm="4">
            <div class="text-caption text-medium-emphasis">Kassenstand</div>
            <div class="text-h6 font-weight-bold" :class="fund.fund_balance_cents >= 0 ? 'text-success' : 'text-error'">
              {{ eur(fund.fund_balance_cents) }}
            </div>
          </v-col>
        </v-row>

        <v-divider class="mb-3" />

        <v-list density="compact">
          <v-list-item
            v-for="b in fund.member_balances"
            :key="b.user_id"
            :class="b.user_id === auth.user?.id ? 'bg-grey-lighten-4 rounded' : ''"
          >
            <template #prepend>
              <v-avatar :color="balanceColor(b.remaining_cents)" variant="tonal" size="36">
                <v-icon icon="mdi-account" size="small" />
              </v-avatar>
            </template>

            <template #title>
              <span :class="b.user_id === auth.user?.id ? 'font-weight-bold' : ''">
                {{ b.display_name }}
                <span v-if="b.user_id === auth.user?.id" class="text-caption ml-1">(du)</span>
              </span>
            </template>

            <template #subtitle>
              Bezahlt: {{ eur(b.total_income_cents) }} von {{ eur(b.share_total_cents) }}
              <span v-if="b.total_standing_order_cents > 0" class="text-caption">
                (davon {{ eur(b.total_standing_order_cents) }} Dauerauftrag)
              </span>
              <span v-if="b.duty_compensation_cents > 0" class="text-caption">
                · +{{ eur(b.duty_compensation_cents) }} Gartenstunden
              </span>
            </template>

            <template #append>
              <div class="text-right">
                <div class="font-weight-bold" :class="b.remaining_cents > 0 ? 'text-error' : 'text-success'">
                  {{ b.remaining_cents > 0 ? '-' : '+' }}{{ eur(Math.abs(b.remaining_cents)) }}
                </div>
                <div class="text-caption" :class="b.remaining_cents > 0 ? 'text-error' : 'text-success'">
                  {{ balanceText(b.remaining_cents) }}
                </div>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </v-card-text>
    </v-card>

    <v-skeleton-loader v-if="loading" type="card" class="mt-6" />
  </div>
</template>

