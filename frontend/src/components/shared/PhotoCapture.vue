<script setup lang="ts">
import { ref } from "vue";
import { api } from "@/api/client";

const props = defineProps<{
  modelValue: string | null;
  label?: string;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string | null): void;
  (e: "uploaded", data: { path: string; filename: string }): void;
}>();

const uploading = ref(false);
const error = ref<string | null>(null);
const previewUrl = ref<string | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const cameraInput = ref<HTMLInputElement | null>(null);

// Build preview URL from path
if (props.modelValue) {
  previewUrl.value = `/api/finance/receipts/${props.modelValue.replace("receipts/", "")}`;
}

function openFilePicker() {
  fileInput.value?.click();
}

function openCamera() {
  cameraInput.value?.click();
}

async function handleFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;

  // Validate client-side
  const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"];
  if (!allowedTypes.includes(file.type)) {
    error.value = "Nur JPEG, PNG oder WebP erlaubt";
    return;
  }
  if (file.size > 10 * 1024 * 1024) {
    error.value = "Datei zu groß (max. 10 MB)";
    return;
  }

  error.value = null;
  uploading.value = true;

  try {
    // Create preview
    previewUrl.value = URL.createObjectURL(file);

    // Upload
    const formData = new FormData();
    formData.append("file", file);

    const token = localStorage.getItem("access_token");
    const response = await fetch("/api/finance/receipts/upload", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Upload fehlgeschlagen");
    }

    const data = await response.json();
    emit("update:modelValue", data.path);
    emit("uploaded", { path: data.path, filename: data.filename });
  } catch (e: any) {
    error.value = e.message || "Upload fehlgeschlagen";
    previewUrl.value = null;
  } finally {
    uploading.value = false;
    // Reset input so same file can be selected again
    input.value = "";
  }
}

function removePhoto() {
  previewUrl.value = null;
  emit("update:modelValue", null);
}
</script>

<template>
  <div>
    <div v-if="previewUrl" class="mb-3">
      <v-img
        :src="previewUrl"
        max-height="200"
        rounded="lg"
        cover
        class="mb-2"
      >
        <template #placeholder>
          <v-row align="center" justify="center" class="fill-height">
            <v-progress-circular indeterminate color="primary" />
          </v-row>
        </template>
      </v-img>
      <v-btn size="small" color="error" variant="text" prepend-icon="mdi-delete" @click="removePhoto">
        Foto entfernen
      </v-btn>
    </div>

    <div v-else class="d-flex ga-2 mb-3">
      <v-btn
        color="primary"
        variant="tonal"
        prepend-icon="mdi-camera"
        :loading="uploading"
        @click="openCamera"
      >
        Kamera
      </v-btn>
      <v-btn
        color="primary"
        variant="outlined"
        prepend-icon="mdi-image"
        :loading="uploading"
        @click="openFilePicker"
      >
        {{ label || "Foto wählen" }}
      </v-btn>
    </div>

    <v-alert v-if="error" type="error" variant="tonal" density="compact" closable class="mb-2" @click:close="error = null">
      {{ error }}
    </v-alert>

    <!-- Hidden file inputs -->
    <input
      ref="fileInput"
      type="file"
      accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
      style="display: none"
      @change="handleFile"
    />
    <input
      ref="cameraInput"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      capture="environment"
      style="display: none"
      @change="handleFile"
    />
  </div>
</template>

