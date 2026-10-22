import { createApp } from "vue";
import "bootstrap/dist/css/bootstrap.min.css";
import "bootstrap"; // the ES build, once: components import { Modal } from the same copy; it needs @popperjs/core (bootstrap's peer, already installed)
import "@fortawesome/fontawesome-free/css/all.min.css";
import "./assets/main.css";

import App from "./App.vue";
import router from "./router";
import { initAuth } from "./stores/auth";
import { registerServiceWorker } from "./push";

const app = createApp(App);
app.use(router);
app.mount("#app");

// Initialise auth after mount so the spinner shows while connecting
initAuth();

// The service worker shows pushed alerts (S021); it caches nothing. A failure is kept quiet
// here and shown on My notifications when the person tries to turn notifications on.
registerServiceWorker();
