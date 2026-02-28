<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
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
  carry_over_cents: number;
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

const currentYear = new Date().getFullYear();
const selectedYear = ref(currentYear);
const yearOptions = computed(() => {
  const years: number[] = [];
  for (let y = currentYear + 1; y >= currentYear - 3; y--) {
    years.push(y);
  }
  return years;
});

const fund = ref<FundOverview | null>(null);
const duty = ref<DutyOverview | null>(null);
const loading = ref(true);

const isCurrentYear = computed(() => selectedYear.value === currentYear);

const myBalance = computed(() => {
  if (!fund.value || !auth.user) return null;
  return fund.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
});

const myDuty = computed(() => {
  if (!duty.value?.member_balances || !auth.user) return null;
  return duty.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
});

const monthsRemaining = computed(() => {
  if (selectedYear.value > currentYear) return 12;
  if (selectedYear.value < currentYear) return 0;
  return Math.max(12 - new Date().getMonth(), 1);
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

async function loadData() {
  loading.value = true;
  try {
    const [fundData, dutyData] = await Promise.all([
      api.get<FundOverview>("/finance/fund/", { year: selectedYear.value }),
      api.get<DutyOverview>(`/duty/overview/${selectedYear.value}`).catch(() => null),
    ]);
    fund.value = fundData;
    duty.value = dutyData;
  } catch {
    // Silently fail
  } finally {
    loading.value = false;
  }
}

watch(selectedYear, () => loadData());
onMounted(() => loadData());
</script>

<template>
  <div>
    <div class="d-flex align-center mb-6">
      <h1 class="text-h4 flex-grow-1">
        Hallo, {{ auth.displayName }}! 👋
      </h1>
      <v-btn-toggle v-model="selectedYear" mandatory density="compact" variant="outlined" color="primary">
        <v-btn v-for="y in yearOptions" :key="y" :value="y" size="small">
          {{ y }}
        </v-btn>
      </v-btn-toggle>
    </div>

    <!-- ═══ My Finance Status ══════════════════════════════════ -->
    <v-card
      v-if="myBalance"
      :color="balanceColor(isCurrentYear ? myBalance.remaining_projected_cents : myBalance.remaining_cents)"
      variant="tonal"
      class="mb-6"
      to="/finance"
    >
      <v-card-text class="pa-4">
        <div class="d-flex align-center mb-3">
          <div class="flex-grow-1">
            <div class="text-body-2 text-medium-emphasis">Deine Finanzen {{ selectedYear }}</div>
          </div>
          <v-icon icon="mdi-cash-register" size="36" />
        </div>

        <!-- ─── Aufschlüsselung Soll ──────────────────────── -->
        <div class="text-body-2 font-weight-bold mb-1">
          <v-icon icon="mdi-arrow-up" size="small" class="mr-1" />
          Jahres-Soll
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
            <tr v-if="myBalance.carry_over_cents > 0">
              <td class="pl-0">Übertrag aus {{ selectedYear - 1 }} (Schulden)</td>
              <td class="text-right pr-0 text-error">+ {{ eur(myBalance.carry_over_cents) }}</td>
            </tr>
            <tr v-if="myBalance.carry_over_cents < 0">
              <td class="pl-0">Übertrag aus {{ selectedYear - 1 }} (Guthaben)</td>
              <td class="text-right pr-0 text-success">- {{ eur(Math.abs(myBalance.carry_over_cents)) }}</td>
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
          {{ isCurrentYear ? 'Bisher eingezahlt' : 'Eingezahlt' }}
        </div>
        <v-table density="compact" class="mb-3 bg-transparent">
          <tbody>
            <tr v-if="myBalance.total_paid_cents > 0">
              <td class="pl-0">Manuelle Einzahlungen</td>
              <td class="text-right pr-0 text-success">{{ eur(myBalance.total_paid_cents) }}</td>
            </tr>
            <tr>
              <td class="pl-0">Daueraufträge{{ isCurrentYear ? ' (bisher abgebucht)' : '' }}</td>
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
          <span class="text-body-2 font-weight-bold">{{ isCurrentYear ? 'Aktuell offen' : 'Ergebnis' }}</span>
          <span class="text-h6 font-weight-bold" :class="myBalance.remaining_cents > 0 ? 'text-error' : 'text-success'">
            {{ myBalance.remaining_cents > 0 ? '' : '+' }}{{ eur(myBalance.remaining_cents > 0 ? myBalance.remaining_cents : Math.abs(myBalance.remaining_cents)) }}
            <span class="text-body-2">{{ myBalance.remaining_cents > 0 ? 'offen' : 'Guthaben' }}</span>
          </span>
        </div>
      </v-card-text>

      <!-- ─── Prognose & Empfehlung (nur aktuelles Jahr) ────── -->
      <template v-if="isCurrentYear">
        <v-divider />
        <v-card-text class="pa-4 pt-3">
          <div class="text-body-2 font-weight-bold mb-2">
            <v-icon icon="mdi-crystal-ball" size="small" class="mr-1" />
            Prognose Ende {{ selectedYear }}
          </div>

          <div class="text-caption mb-2">
            Daueraufträge geplant (ganzes Jahr): {{ eur(myBalance.total_standing_order_projected_cents) }}
            · Gesamt-Prognose: {{ eur(myBalance.total_income_projected_cents) }}
          </div>

          <template v-if="myBalance.remaining_projected_cents <= 0">
            <v-chip color="success" variant="flat" size="small" class="mr-2">
              <v-icon icon="mdi-check-circle" start size="small" />
              Alles gedeckt!
            </v-chip>
            <span v-if="myBalance.remaining_projected_cents < 0" class="text-body-2">
              {{ eur(Math.abs(myBalance.remaining_projected_cents)) }} Guthaben erwartet
            </span>
          </template>

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
      </template>
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
        Kassenübersicht {{ selectedYear }}
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
            three-line
          >
            <template #prepend>
              <v-avatar
                :color="balanceColor(isCurrentYear ? b.remaining_projected_cents : b.remaining_cents)"
                variant="tonal"
                size="36"
              >
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
              <div>
                Bezahlt: {{ eur(b.total_income_cents) }} von {{ eur(b.share_total_cents) }}
                <span v-if="b.total_standing_order_cents > 0" class="text-caption">
                  ({{ eur(b.total_standing_order_cents) }} Dauerauftrag)
                </span>
                <span v-if="b.duty_compensation_cents > 0" class="text-caption">
                  · +{{ eur(b.duty_compensation_cents) }} Gartenstunden
                </span>
              </div>
              <!-- Prognose-Zeile (nur aktuelles Jahr) -->
              <div v-if="isCurrentYear" class="mt-1">
                <template v-if="b.remaining_projected_cents <= 0">
                  <v-icon icon="mdi-check-circle" size="x-small" color="success" class="mr-1" />
                  <span class="text-caption text-success">
                    Schätzung Ende {{ selectedYear }}: gedeckt
                    <span v-if="b.remaining_projected_cents < 0">
                      · ca. {{ eur(Math.abs(b.remaining_projected_cents)) }} Rückzahlung
                    </span>
                  </span>
                </template>
                <template v-else>
                  <v-icon icon="mdi-alert" size="x-small" color="error" class="mr-1" />
                  <span class="text-caption text-error">
                    Schätzung Ende {{ selectedYear }}: ca. {{ eur(b.remaining_projected_cents) }} Nachzahlung
                  </span>
                </template>
                <div class="text-caption text-medium-emphasis" style="font-size: 0.65rem !important;">
                  * basierend auf aktuellen Daueraufträgen & Umlagen
                </div>
              </div>
            </template>

            <template #append>
              <div class="text-right">
                <!-- Aktueller Stand -->
                <div class="font-weight-bold" :class="b.remaining_cents > 0 ? 'text-error' : 'text-success'">
                  {{ eur(Math.abs(b.remaining_cents)) }}
                </div>
                <div class="text-caption" :class="b.remaining_cents > 0 ? 'text-error' : 'text-success'">
                  {{ b.remaining_cents > 0 ? 'offen' : b.remaining_cents < 0 ? 'Guthaben' : '✓' }}
                </div>

                <!-- Prognose Ende Jahr (nur aktuelles Jahr) -->
                <div v-if="isCurrentYear" class="mt-1">
                  <div
                    class="text-caption font-weight-bold"
                    :class="b.remaining_projected_cents > 0 ? 'text-error' : 'text-success'"
                  >
                    → ca. {{ eur(Math.abs(b.remaining_projected_cents)) }}
                    <span class="font-weight-regular">
                      {{ b.remaining_projected_cents > 0 ? 'Nachzahlung*' : b.remaining_projected_cents < 0 ? 'Guthaben*' : 'ausgeglichen*' }}
                    </span>
                  </div>
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
