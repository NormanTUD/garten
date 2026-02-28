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
      :color="balanceColor(myBalance.remaining_projected_cents)"
      variant="tonal"
      class="mb-6"
      to="/finance"
    >
      <v-card-text class="pa-4">
        <div class="d-flex align-center mb-3">
          <div class="flex-grow-1">
            <div class="text-body-2 text-medium-emphasis">Deine Finanzen {{ new Date().getFullYear() }}</div>
          </div>
          <v-icon icon="mdi-cash-register" size="36" />
        </div>

        <!-- ─── Aufschlüsselung Soll ──────────────────────── -->
        <div class="text-body-2 font-weight-bold mb-1">
          <v-icon icon="mdi-arrow-up" size="small" class="mr-1" />
          Dein Jahres-Soll
        </div>
        <v-table density="compact" class="mb-3 bg-transparent">
          <tbody>
            <tr>
              <td class="pl-0">Laufende Kosten (dein Anteil)</td>
              <td class="text-right pr-0">{{ eur(myBalance.share_recurring_cents) }}</td>
            </tr>
            <tr v-if="myBalance.share_onetime_cents > 0">
              <td class="pl-0">Einmal-Umlagen</td>
              <td class="text-right pr-0">{{ eur(myBalance.share_onetime_cents) }}</td>
            </tr>
            <tr v-if="myBalance.duty_compensation_cents > 0">
              <td class="pl-0">Ausgleich Gartenstunden</td>
              <td class="text-right pr-0 text-error">+ {{ eur(myBalance.duty_compensation_cents) }}</td>
            </tr>
            <tr class="font-weight-bold">
              <td class="pl-0">Gesamt-Soll</td>
              <td class="text-right pr-0">{{ eur(myBalance.share_total_cents) }}</td>
            </tr>
          </tbody>
        </v-table>

        <!-- ─── Aufschlüsselung Haben ─────────────────────── -->
        <div class="text-body-2 font-weight-bold mb-1">
          <v-icon icon="mdi-arrow-down" size="small" class="mr-1" />
          Bisher eingezahlt
        </div>
        <v-table density="compact" class="mb-3 bg-transparent">
          <tbody>
            <tr v-if="myBalance.total_paid_cents > 0">
              <td class="pl-0">Manuelle Einzahlungen</td>
              <td class="text-right pr-0 text-success">{{ eur(myBalance.total_paid_cents) }}</td>
            </tr>
            <tr>
              <td class="pl-0">Daueraufträge (bisher abgebucht)</td>
              <td class="text-right pr-0 text-success">{{ eur(myBalance.total_standing_order_cents) }}</td>
            </tr>
            <tr class="font-weight-bold">
              <td class="pl-0">Gesamt eingezahlt</td>
              <td class="text-right pr-0 text-success">{{ eur(myBalance.total_income_cents) }}</td>
            </tr>
          </tbody>
        </v-table>

        <!-- ─── Aktueller Stand ────────────────────────────── -->
        <v-divider class="mb-3" />
        <div class="d-flex justify-space-between align-center mb-1">
          <span class="text-body-2 font-weight-bold">Aktuell offen</span>
          <span class="text-h6 font-weight-bold" :class="myBalance.remaining_cents > 0 ? 'text-error' : 'text-success'">
            {{ myBalance.remaining_cents > 0 ? '' : '+' }}{{ eur(myBalance.remaining_cents > 0 ? myBalance.remaining_cents : Math.abs(myBalance.remaining_cents)) }}
            <span class="text-body-2">{{ myBalance.remaining_cents > 0 ? 'offen' : 'Guthaben' }}</span>
          </span>
        </div>
      </v-card-text>

      <!-- ─── Prognose & Empfehlung ─────────────────────────── -->
      <v-divider />
      <v-card-text class="pa-4 pt-3">
        <div class="text-body-2 font-weight-bold mb-2">
          <v-icon icon="mdi-crystal-ball" size="small" class="mr-1" />
          Prognose Ende {{ new Date().getFullYear() }}
        </div>

        <div class="text-caption mb-2">
          Daueraufträge geplant (ganzes Jahr): {{ eur(myBalance.total_standing_order_projected_cents) }}
          · Gesamt-Prognose: {{ eur(myBalance.total_income_projected_cents) }}
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
          <v-chip color="error" variant="tonal" size="small" class="mb-2">
            <v-icon icon="mdi-alert" start size="small" />
            {{ eur(myBalance.remaining_projected_cents) }} offen Ende Jahr
          </v-chip>

          <div class="text-body-2 mt-2">
            <v-icon icon="mdi-lightbulb-outline" size="small" class="mr-1" />
            <strong>Empfehlung:</strong>
          </div>
          <div class="text-body-2 ml-6">
            • Abschlag erhöhen um
            <strong>{{ eur(Math.ceil(myBalance.remaining_projected_cents / monthsRemaining / 100) * 100) }}/Monat</strong>
            ({{ monthsRemaining }} Monate übrig)
          </div>
          <div class="text-body-2 ml-6">
            • Oder einmalig <strong>{{ eur(myBalance.remaining_projected_cents) }}</strong> einzahlen
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

