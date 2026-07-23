<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";
import { useStatsStore } from "@/stores/stats";
import MIcon from "@/components/common/MIcon.vue";

const route = useRoute();
const statsStore = useStatsStore();

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    "/dashboard": "仪表盘",
    "/tasks": "下载器",
    "/channels": "订阅源",
    "/media": "媒体库",
    "/settings": "设置",
  };
  return titles[route.path] || "TGMedia";
});
</script>

<template>
  <header
    class="flex h-13 items-center justify-between border-b border-surface-border bg-surface-2 px-5"
  >
    <h1 class="text-base font-semibold tracking-tight">{{ pageTitle }}</h1>

    <div class="flex items-center gap-4 text-sm text-text-secondary">
      <div
        v-if="statsStore.stats.downloading > 0"
        class="flex items-center gap-1.5 font-mono text-xs"
      >
        <span class="text-primary">
          {{ statsStore.formattedSpeed }}
        </span>
      </div>

      <div class="flex items-center gap-1.5">
        <MIcon
          name="circle"
          :size="8"
          filled
          :class="statsStore.connected ? 'text-primary' : 'text-danger'"
        />
        <span class="text-xs">
          {{ statsStore.connected ? "已连接" : "未连接" }}
        </span>
      </div>
    </div>
  </header>
</template>
