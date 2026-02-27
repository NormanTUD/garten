import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { api } from "@/api/client";
import type { ApiError } from "@/api/client";

interface User {
  id: number;
  username: string;
  display_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export const useAuthStore = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => user.value !== null);
  const isAdmin = computed(() => user.value?.role === "admin");
  const displayName = computed(() => user.value?.display_name || "");

  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true;
    error.value = null;

    try {
      await api.login(username, password);
      await fetchUser();
      return true;
    } catch (e) {
      const apiError = e as ApiError;
      error.value = apiError.detail || "Login fehlgeschlagen";
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function fetchUser(): Promise<void> {
    try {
      user.value = await api.get<User>("/auth/me");
    } catch {
      user.value = null;
      api.clearTokens();
    }
  }

  async function logout(): Promise<void> {
    api.logout();
    user.value = null;
  }

  async function initialize(): Promise<void> {
    const token = localStorage.getItem("access_token");
    if (token) {
      await fetchUser();
    }
  }

  async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await api.put("/auth/me/password", {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    displayName,
    login,
    logout,
    fetchUser,
    initialize,
    changePassword,
  };
});

