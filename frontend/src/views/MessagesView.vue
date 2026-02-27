<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { api } from "@/api/client";
import { useAuthStore } from "@/stores/auth";

const auth = useAuthStore();

interface UserSummary {
  id: number;
  display_name: string;
}

interface Message {
  id: number;
  sender_id: number | null;
  sender: UserSummary | null;
  recipient_id: number;
  recipient: UserSummary;
  subject: string;
  body: string;
  message_type: string;
  is_read: boolean;
  is_archived: boolean;
  related_entity: string | null;
  related_entity_id: number | null;
  created_at: string;
}

interface MemberBalance {
  user_id: number;
  display_name: string;
}

interface FundOverview {
  member_balances: MemberBalance[];
}

// State
const tab = ref("inbox");
const loading = ref(true);
const inbox = ref<Message[]>([]);
const sent = ref<Message[]>([]);
const users = ref<UserSummary[]>([]);
const selectedMessage = ref<Message | null>(null);
const showMessageDialog = ref(false);
const showComposeDialog = ref(false);
const showBroadcastDialog = ref(false);

const composeForm = ref({
  recipient_id: null as number | null,
  subject: "",
  body: "",
});

const broadcastForm = ref({
  subject: "",
  body: "",
});

const unreadInbox = computed(() => inbox.value.filter((m) => !m.is_read));
const readInbox = computed(() => inbox.value.filter((m) => m.is_read));

// Load
onMounted(() => loadAll());

async function loadAll() {
  loading.value = true;
  try {
    const [inboxData, sentData, fundData] = await Promise.all([
      api.get<Message[]>("/messages/"),
      api.get<Message[]>("/messages/sent"),
      api.get<FundOverview>("/finance/fund/"),
    ]);
    inbox.value = inboxData;
    sent.value = sentData;
    users.value = fundData.member_balances
      .filter((b) => b.user_id !== auth.user?.id)
      .map((b) => ({ id: b.user_id, display_name: b.display_name }));
  } finally {
    loading.value = false;
  }
}

// Helpers
function timeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return "gerade eben";
  if (diffMin < 60) return `vor ${diffMin} Min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `vor ${diffH} Std`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 7) return `vor ${diffD} Tagen`;
  return new Date(dateStr).toLocaleDateString("de-DE");
}

function senderName(msg: Message): string {
  if (msg.sender) return msg.sender.display_name;
  if (msg.message_type.startsWith("auto:")) return "🤖 Automatisch";
  if (msg.message_type === "broadcast") return "📢 Rundnachricht";
  return "🌱 System";
}

function messageIcon(msg: Message): string {
  if (msg.message_type === "broadcast") return "mdi-bullhorn";
  if (msg.message_type.startsWith("auto:")) return "mdi-robot";
  if (msg.message_type === "system") return "mdi-information";
  return "mdi-email";
}

function messageColor(msg: Message): string {
  if (msg.message_type === "broadcast") return "info";
  if (msg.message_type.startsWith("auto:")) return "warning";
  if (msg.message_type === "system") return "primary";
  return "default";
}

// Actions
async function openMessage(msg: Message) {
  // Mark as read via GET
  const data = await api.get<Message>(`/messages/${msg.id}`);
  selectedMessage.value = data;
  showMessageDialog.value = true;
  // Update local state
  const idx = inbox.value.findIndex((m) => m.id === msg.id);
  if (idx >= 0) inbox.value[idx].is_read = true;
}

async function archiveMessage(id: number) {
  await api.patch(`/messages/${id}`, { is_archived: true });
  showMessageDialog.value = false;
  await loadAll();
}

async function deleteMessage(id: number) {
  await api.delete(`/messages/${id}`);
  showMessageDialog.value = false;
  await loadAll();
}

async function markAllRead() {
  await api.post("/messages/mark-all-read");
  await loadAll();
}

function openCompose(recipientId?: number) {
  composeForm.value = {
    recipient_id: recipientId || null,
    subject: "",
    body: "",
  };
  showComposeDialog.value = true;
}

function openReply(msg: Message) {
  if (!msg.sender) return;
  composeForm.value = {
    recipient_id: msg.sender.id,
    subject: msg.subject.startsWith("Re: ") ? msg.subject : `Re: ${msg.subject}`,
    body: "",
  };
  showMessageDialog.value = false;
  showComposeDialog.value = true;
}

async function sendMessage() {
  if (!composeForm.value.recipient_id || !composeForm.value.subject || !composeForm.value.body) return;
  await api.post("/messages/", composeForm.value);
  showComposeDialog.value = false;
  await loadAll();
}

function openBroadcast() {
  broadcastForm.value = { subject: "", body: "" };
  showBroadcastDialog.value = true;
}

async function sendBroadcast() {
  if (!broadcastForm.value.subject || !broadcastForm.value.body) return;
  await api.post("/messages/broadcast", {
    recipient_id: 0,
    subject: broadcastForm.value.subject,
    body: broadcastForm.value.body,
  });
  showBroadcastDialog.value = false;
  await loadAll();
}
</script>

<template>
  <div>
    <div class="d-flex align-center mb-4 flex-wrap ga-2">
      <h1 class="text-h4">Nachrichten</h1>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-pencil" @click="openCompose()">Neue Nachricht</v-btn>
      <v-btn v-if="auth.isAdmin" color="info" variant="tonal" prepend-icon="mdi-bullhorn" @click="openBroadcast">Rundnachricht</v-btn>
    </div>

    <v-skeleton-loader v-if="loading" type="list-item@5" />

    <template v-else>
      <v-tabs v-model="tab" color="primary" class="mb-4">
        <v-tab value="inbox">
          <v-icon start icon="mdi-inbox" />
          Posteingang
          <v-badge v-if="unreadInbox.length" :content="unreadInbox.length" color="error" inline class="ml-2" />
        </v-tab>
        <v-tab value="sent">
          <v-icon start icon="mdi-send" />
          Gesendet ({{ sent.length }})
        </v-tab>
      </v-tabs>

      <v-window v-model="tab">
        <!-- ─── Inbox ──────────────────────────────────────── -->
        <v-window-item value="inbox">
          <div v-if="inbox.length === 0" class="text-center py-8">
            <v-icon icon="mdi-email-open-outline" size="64" color="grey" />
            <p class="text-body-1 text-grey mt-2">Keine Nachrichten</p>
          </div>

          <template v-else>
            <div v-if="unreadInbox.length > 0" class="d-flex align-center mb-2">
              <span class="text-body-2 text-medium-emphasis">{{ unreadInbox.length }} ungelesen</span>
              <v-spacer />
              <v-btn size="small" variant="text" prepend-icon="mdi-email-open" @click="markAllRead">Alle gelesen</v-btn>
            </div>

            <v-list lines="three">
              <v-list-item
                v-for="msg in inbox"
                :key="msg.id"
                :class="!msg.is_read ? 'bg-blue-lighten-5' : ''"
                @click="openMessage(msg)"
                style="cursor: pointer"
              >
                <template #prepend>
                  <v-avatar :color="messageColor(msg)" variant="tonal" size="40">
                    <v-icon :icon="messageIcon(msg)" size="small" />
                  </v-avatar>
                </template>

                <template #title>
                  <span :class="!msg.is_read ? 'font-weight-bold' : ''">{{ msg.subject }}</span>
                </template>

                <template #subtitle>
                  <span class="text-caption">{{ senderName(msg) }} · {{ timeAgo(msg.created_at) }}</span>
                  <br />
                  <span class="text-body-2 text-medium-emphasis">{{ msg.body.substring(0, 100) }}{{ msg.body.length > 100 ? '...' : '' }}</span>
                </template>

                <template #append>
                  <v-icon v-if="!msg.is_read" icon="mdi-circle" color="primary" size="x-small" />
                </template>
              </v-list-item>
            </v-list>
          </template>
        </v-window-item>

        <!-- ─── Sent ───────────────────────────────────────── -->
        <v-window-item value="sent">
          <div v-if="sent.length === 0" class="text-center py-8">
            <v-icon icon="mdi-send-outline" size="64" color="grey" />
            <p class="text-body-1 text-grey mt-2">Noch keine Nachrichten gesendet</p>
          </div>

          <v-list v-else lines="three">
            <v-list-item v-for="msg in sent" :key="msg.id" @click="openMessage(msg)" style="cursor: pointer">
              <template #prepend>
                <v-avatar color="default" variant="tonal" size="40">
                  <v-icon icon="mdi-send" size="small" />
                </v-avatar>
              </template>

              <template #title>
                <span>An: {{ msg.recipient.display_name }}</span>
              </template>

              <template #subtitle>
                <span class="font-weight-medium">{{ msg.subject }}</span>
                <br />
                <span class="text-caption">{{ timeAgo(msg.created_at) }}</span>
              </template>
            </v-list-item>
          </v-list>
        </v-window-item>
      </v-window>
    </template>

    <!-- ═══ Read Message Dialog ════════════════════════════════ -->
    <v-dialog v-model="showMessageDialog" max-width="600">
      <v-card v-if="selectedMessage">
        <v-card-title class="d-flex align-center">
          <v-icon :icon="messageIcon(selectedMessage)" :color="messageColor(selectedMessage)" class="mr-2" />
          {{ selectedMessage.subject }}
        </v-card-title>

        <v-card-subtitle>
          <span class="font-weight-medium">{{ senderName(selectedMessage) }}</span>
          · {{ new Date(selectedMessage.created_at).toLocaleString('de-DE') }}
          <v-chip size="x-small" variant="tonal" class="ml-2">{{ selectedMessage.message_type }}</v-chip>
        </v-card-subtitle>

        <v-divider class="mt-2" />

        <v-card-text class="text-body-1" style="white-space: pre-wrap;">{{ selectedMessage.body }}</v-card-text>

        <v-divider />

        <v-card-actions>
          <v-btn v-if="selectedMessage.sender" variant="tonal" prepend-icon="mdi-reply" @click="openReply(selectedMessage)">Antworten</v-btn>
          <v-btn variant="tonal" color="warning" prepend-icon="mdi-archive" @click="archiveMessage(selectedMessage.id)">Archivieren</v-btn>
          <v-spacer />
          <v-btn variant="text" color="error" prepend-icon="mdi-delete" @click="deleteMessage(selectedMessage.id)">Löschen</v-btn>
          <v-btn variant="text" @click="showMessageDialog = false">Schließen</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Compose Dialog ═════════════════════════════════════ -->
    <v-dialog v-model="showComposeDialog" max-width="600">
      <v-card>
        <v-card-title><v-icon icon="mdi-pencil" class="mr-2" />Neue Nachricht</v-card-title>
        <v-card-text>
          <v-form @submit.prevent="sendMessage">
            <v-select
              v-model="composeForm.recipient_id"
              label="An *"
              :items="users"
              item-title="display_name"
              item-value="id"
              variant="outlined"
              density="comfortable"
              class="mb-3"
            />
            <v-text-field
              v-model="composeForm.subject"
              label="Betreff *"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              autofocus
            />
            <v-textarea
              v-model="composeForm.body"
              label="Nachricht *"
              variant="outlined"
              density="comfortable"
              rows="6"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showComposeDialog = false">Abbrechen</v-btn>
          <v-btn
            color="primary"
            prepend-icon="mdi-send"
            :disabled="!composeForm.recipient_id || !composeForm.subject || !composeForm.body"
            @click="sendMessage"
          >
            Senden
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- ═══ Broadcast Dialog (Admin) ═══════════════════════════ -->
    <v-dialog v-model="showBroadcastDialog" max-width="600">
      <v-card>
        <v-card-title><v-icon icon="mdi-bullhorn" color="info" class="mr-2" />Rundnachricht an alle</v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-3">
            Diese Nachricht wird an alle aktiven Mitglieder gesendet.
          </v-alert>
          <v-form @submit.prevent="sendBroadcast">
            <v-text-field
              v-model="broadcastForm.subject"
              label="Betreff *"
              variant="outlined"
              density="comfortable"
              class="mb-3"
              autofocus
            />
            <v-textarea
              v-model="broadcastForm.body"
              label="Nachricht *"
              variant="outlined"
              density="comfortable"
              rows="6"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showBroadcastDialog = false">Abbrechen</v-btn>
          <v-btn
            color="info"
            prepend-icon="mdi-send"
            :disabled="!broadcastForm.subject || !broadcastForm.body"
            @click="sendBroadcast"
          >
            An alle senden
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

