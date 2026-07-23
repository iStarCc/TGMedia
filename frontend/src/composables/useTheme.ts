import { ref, watchEffect } from "vue";

type Theme = "system" | "light" | "dark";

const STORAGE_KEY = "tgmedia-theme";

const theme = ref<Theme>((localStorage.getItem(STORAGE_KEY) as Theme) || "system");

function applyTheme(t: Theme) {
  const root = document.documentElement;
  root.classList.remove("light", "dark");

  if (t === "dark") {
    root.classList.add("dark");
  } else if (t === "light") {
    root.classList.add("light");
  }
  // "system" falls through to prefers-color-scheme media query
}

watchEffect(() => {
  applyTheme(theme.value);
  localStorage.setItem(STORAGE_KEY, theme.value);
});

export function useTheme() {
  function setTheme(t: Theme) {
    theme.value = t;
  }

  function cycle() {
    const order: Theme[] = ["system", "light", "dark"];
    const idx = order.indexOf(theme.value);
    theme.value = order[(idx + 1) % order.length];
  }

  return { theme, setTheme, cycle };
}
