import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const routes = [
  {
    path: "/login",
    name: "login",
    component: () => import("@/views/LoginView.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    name: "dashboard",
    component: () => import("@/views/DashboardView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/garden",
    name: "garden",
    component: () => import("@/views/GardenView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/harvest",
    name: "harvest",
    component: () => import("@/views/HarvestView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/watering",
    name: "watering",
    component: () => import("@/views/WateringView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/finance",
    name: "finance",
    component: () => import("@/views/FinanceView.vue"),
    meta: { requiresAuth: true },
  },
  {
    path: "/admin",
    name: "admin",
    component: () => import("@/views/AdminView.vue"),
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
	  path: "/messages",
	  name: "messages",
	  component: () => import("@/views/MessagesView.vue"),
		  meta: { requiresAuth: true },
  },
  {
    path: "/duty",
    name: "duty",
    component: () => import("@/views/DutyView.vue"),
    meta: { requiresAuth: true },
  },

];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();

  if (!auth.isAuthenticated && localStorage.getItem("access_token")) {
    await auth.initialize();
  }

  if (to.meta.requiresAuth && !auth.isAuthenticated) {
    return { name: "login" };
  }

  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { name: "dashboard" };
  }

  if (to.name === "login" && auth.isAuthenticated) {
    return { name: "dashboard" };
  }
});

export default router;

