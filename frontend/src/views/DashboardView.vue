<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface Stats {
  gardens: number;
  beds: number;
  plants: number;
  harvests: number;
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
  total_costs_annual_cents: number;
  total_income_cents: number;
  fund_balance_cents: number;
  share_recurring_per_member_monthly_cents: number;
  share_total_per_member_annual_cents: number;
  member_count: number;
  member_balances: MemberBalance[];
}

const stats = ref<Stats>({ gardens: 0, beds: 0, plants: 0, harvests: 0 });
const fund = ref<FundOverview | null>(null);
const loading = ref(true);

const myBalance = computed(() => {
  if (!fund.value || !auth.user) return null;
  return fund.value.member_balances.find((b) => b.user_id === auth.user!.id) || null;
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

onMounted(async () => {
  try {
    const [gardens, plants, harvests, fundData] = await Promise.all([
      api.get<any[]>("/gardens/"),
      api.get<any[]>("/plants/"),
      api.get<any[]>("/harvests/"),
      api.get<FundOverview>("/finance/fund/"),
    ]);

    stats.value.gardens = gardens.length;
    stats.value.plants = plants.length;
    stats.value.harvests = harvests.length;
    fund.value = fundData;

    let bedCount = 0;
    for (const garden of gardens) {
      const beds = await api.get<any[]>("/beds/", { garden_id: garden.id });
      bedCount += beds.length;
    }
    stats.value.beds = bedCount;
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

    <!-- ═══ My Finance Status (prominent) ══════════════════════ -->
    <v-card
      v-if="myBalance"
      :color="balanceColor(myBalance.remaining_cents)"
      variant="tonal"
      class="mb-6"
      to="/finance"
    >
      <v-card-text class="d-flex align-center pa-4">
        <div class="flex-grow-1">
          <div class="text-body-2 text-medium-emphasis">Dein Kassenstand</div>
          <div class="text-h4 font-weight-bold my-1">
            {{ eur(Math.abs(myBalance.remaining_cents)) }}
          </div>
          <div class="text-body-2">{{ balanceText(myBalance.remaining_cents) }}</div>
          <div class="text-caption mt-1">
            Soll: {{ eur(myBalance.share_total_cents) }}
            · Eingezahlt: {{ eur(myBalance.total_income_cents) }}
          </div>
        </div>
        <div class="text-right">
          <v-icon icon="mdi-cash-register" size="48" class="mb-2" />
          <div class="text-caption">
            {{ eur(fund!.share_recurring_per_member_monthly_cents) }} / Monat
          </div>
        </div>
      </v-card-text>
    </v-card>

    <!-- ═══ Garden Stats ═══════════════════════════════════════ -->
    <!--
    <v-row>
      <v-col cols="6" md="3">
        <v-card color="primary" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-flower" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.gardens }}</div>
            <div class="text-body-2">Gärten</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card color="secondary" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-grid" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.beds }}</div>
            <div class="text-body-2">Beete</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card color="accent" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-leaf" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.plants }}</div>
            <div class="text-body-2">Pflanzen</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" md="3">
        <v-card color="success" variant="tonal">
          <v-card-text class="text-center">
            <v-icon icon="mdi-basket" size="40" class="mb-2" />
            <div class="text-h4 font-weight-bold">{{ stats.harvests }}</div>
            <div class="text-body-2">Ernten</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
    -->

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
