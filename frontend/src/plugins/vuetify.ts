import "@mdi/font/css/materialdesignicons.css";
import "vuetify/styles";

import { createVuetify } from "vuetify";
import * as components from "vuetify/components";
import * as directives from "vuetify/directives";

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: "gartenTheme",
    themes: {
      gartenTheme: {
        dark: false,
        colors: {
          primary: "#2E7D32",
          secondary: "#81C784",
          accent: "#FFC107",
          error: "#D32F2F",
          warning: "#F57C00",
          info: "#1976D2",
          success: "#388E3C",
          background: "#F5F5F5",
          surface: "#FFFFFF",
        },
      },
    },
  },
  defaults: {
    VBtn: {
      rounded: "lg",
    },
    VCard: {
      rounded: "lg",
      elevation: 2,
    },
    VTextField: {
      variant: "outlined",
      density: "comfortable",
    },
    VSelect: {
      variant: "outlined",
      density: "comfortable",
    },
  },
});

