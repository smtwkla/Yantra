import { createApp } from "vue";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap/dist/js/bootstrap.bundle.min.js";
import "@fortawesome/fontawesome-free/css/all.min.css";
import "./assets/main.css";

import App from "./App.vue";
import router from "./router";
import { initAuth } from "./stores/auth";

const app = createApp(App);
app.use(router);
app.mount("#app");

// Initialise auth after mount so the spinner shows while connecting
initAuth();
