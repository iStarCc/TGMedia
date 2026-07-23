<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useTheme } from "@/composables/useTheme";
import { useStatsStore } from "@/stores/stats";
import { APP_VERSION } from "@/constants/app";
import MIcon from "@/components/common/MIcon.vue";
import { PhGithubLogo } from "@phosphor-icons/vue";

const route = useRoute();
const { theme, cycle } = useTheme();
const statsStore = useStatsStore();
const baseUrl = import.meta.env.BASE_URL;

const navItems = [
  { path: "/dashboard", label: "仪表盘", icon: "analytics" },
  { path: "/channels", label: "订阅源", icon: "rss_feed" },
  { path: "/tasks", label: "下载器", icon: "download" },
  { path: "/media", label: "媒体库", icon: "photo_library" },
  { path: "/settings", label: "设置", icon: "settings" },
];

const currentPath = computed(() => route.path);

const activeTaskCount = computed(() => {
  const { downloading, pending } = statsStore.stats;
  return downloading + pending;
});

const themeIcon = computed(() => {
  if (theme.value === "light") return "light_mode";
  if (theme.value === "dark") return "dark_mode";
  return "desktop_windows";
});

const themeLabel = computed(() => {
  const map = { system: "跟随系统", light: "浅色", dark: "深色" };
  return map[theme.value];
});
</script>

<template>
  <aside
    class="grid h-full w-56 shrink-0 grid-rows-[auto_minmax(0,1fr)_auto] border-r border-surface-border bg-surface-2 px-3 py-3"
  >
    <div class="mb-2 flex items-center gap-2 px-1">
      <img :src="`${baseUrl}logo.png`" alt="TGMedia" class="h-8 w-8 rounded-lg" />
      <span class="text-base font-semibold tracking-tight">TGMedia</span>
    </div>

    <nav class="overflow-y-auto overscroll-contain py-1 -mx-1 px-1">
      <div class="flex flex-col gap-0.5">
        <RouterLink
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors duration-150 cursor-pointer"
          :class="
            currentPath === item.path
              ? 'bg-primary/10 text-primary font-medium'
              : 'text-text-secondary hover:bg-surface hover:text-text-primary'
          "
        >
          <MIcon :name="item.icon" :size="18" />
          <span class="flex-1">{{ item.label }}</span>
          <span
            v-if="item.path === '/tasks' && activeTaskCount > 0"
            class="min-w-4 rounded-full bg-danger px-1 text-center text-[10px] font-medium leading-4 text-white animate-pulse"
          >
            {{ activeTaskCount > 99 ? '99+' : activeTaskCount }}
          </span>
        </RouterLink>
      </div>
    </nav>

    <div class="space-y-1 border-t border-surface-border pt-2">
      <button
        class="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-text-muted hover:text-text-secondary cursor-pointer transition-colors"
        @click="cycle"
      >
        <MIcon :name="themeIcon" :size="14" />
        <span>{{ themeLabel }}</span>
      </button>
      <a
        href="https://github.com/iStarCc/TGMedia"
        target="_blank"
        rel="noopener noreferrer"
        class="flex items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
      >
        <PhGithubLogo :size="14" />
        <span>v{{ APP_VERSION }}</span>
      </a>
    </div>
  </aside>
</template>
