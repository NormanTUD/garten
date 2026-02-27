import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import vuetify from "./plugins/vuetify";
import router from "./router";

const app = createApp(App);

app.use(createPinia());
app.use(vuetify);
app.use(router);

app.mount("#app");

// PWA Update Notification
if ("serviceWorker" in navigator) {
  navigator.serviceWorker.ready.then((registration) => {
    registration.addEventListener("updatefound", () => {
      const newWorker = registration.installing;
      if (newWorker) {
        newWorker.addEventListener("statechange", () => {
          if (newWorker.state === "activated") {
            // New version available – could show a snackbar here
            console.log("[PWA] Neue Version verfügbar. Seite wird aktualisiert...");
          }
        });
      }
    });
  });
}

