import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import router from "./router";
import "./assets/main.css";

async function bootstrap() {
  const timeout = new Promise<void>((resolve) => setTimeout(resolve, 2500));
  const loadIcons = document.fonts
    .load('400 24px "Material Symbols Rounded"')
    .catch(() => undefined);
  await Promise.race([Promise.all([loadIcons, document.fonts.ready]), timeout]);
  document.documentElement.classList.add("icons-ready");

  const app = createApp(App);
  app.use(createPinia());
  app.use(router);
  app.mount("#app");
}

bootstrap();
