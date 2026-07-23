<script setup lang="ts">
import MIcon from "@/components/common/MIcon.vue";
import { PhGithubLogo } from "@phosphor-icons/vue";
import { storeToRefs } from "pinia";
import { useVersionStore } from "@/stores/version";

const baseUrl = import.meta.env.BASE_URL;
const versionStore = useVersionStore();
const { hasUpdate, latest, current, remoteUrl, checkError, changelog, loading } = storeToRefs(versionStore);

const tagStyles: Record<string, string> = {
  新功能: "bg-primary/10 text-primary",
  修复: "bg-warning/10 text-warning",
  优化: "bg-info/10 text-info",
  其他: "bg-surface text-text-muted",
};

function tagClass(type: string): string {
  return tagStyles[type] ?? tagStyles.其他;
}

const metaCards = [
  { icon: "layers", label: "技术栈", value: "TDLib · FastAPI · Vue 3" },
  { icon: "dns", label: "运行平台", value: "飞牛 fnOS" },
  { icon: "code", label: "开源协议", value: "MIT License" },
  { icon: "person", label: "开发者", value: "iStarCc" },
];
</script>

<template>
  <div class="space-y-6">
    <section
      v-if="hasUpdate"
      class="flex items-center justify-between gap-3 rounded-xl border border-primary/30 bg-primary/5 px-4 py-3"
    >
      <div class="flex items-center gap-2 text-sm">
        <MIcon name="system_update" :size="18" class="text-primary" />
        <span>
          发现新版本 <strong class="font-mono">v{{ latest }}</strong>，当前 v{{ current }}
        </span>
      </div>
      <a
        :href="remoteUrl"
        target="_blank"
        rel="noopener noreferrer"
        class="shrink-0 rounded-lg bg-primary px-3 py-1.5 text-xs text-white hover:bg-primary-hover transition-colors"
      >
        前往 GitHub
      </a>
    </section>

    <p v-else-if="checkError" class="text-xs text-text-muted text-center">{{ checkError }}</p>

    <!-- Hero -->
    <section class="relative overflow-hidden rounded-2xl border border-surface-border bg-surface-2">
      <div class="absolute inset-0 bg-gradient-to-br from-primary/[0.07] via-transparent to-info/[0.05]" />
      <div class="absolute -right-8 -top-8 h-40 w-40 rounded-full bg-primary/[0.04] blur-2xl" />
      <div class="absolute -bottom-12 -left-8 h-32 w-32 rounded-full bg-info/[0.04] blur-2xl" />

      <div class="relative px-8 py-10">
        <div class="flex flex-col sm:flex-row sm:items-center gap-6">
          <img
            :src="`${baseUrl}logo.png`"
            alt="TGMedia"
            class="h-[4.5rem] w-[4.5rem] rounded-2xl shadow-md ring-1 ring-surface-border/80"
          />
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-3">
              <h2 class="text-2xl font-semibold tracking-tight">TGMedia</h2>
              <span class="rounded-full bg-primary/10 px-2.5 py-0.5 text-xs font-mono font-medium text-primary">
                v{{ current }}
              </span>
            </div>
            <p class="mt-1.5 text-sm text-text-secondary leading-relaxed">
              Telegram 频道媒体实时下载与管理工具
            </p>
            <a
              :href="remoteUrl"
              target="_blank"
              rel="noopener noreferrer"
              class="mt-4 inline-flex items-center gap-2 rounded-lg border border-surface-border bg-surface/60 px-3.5 py-2 text-xs text-text-secondary hover:text-text-primary hover:border-primary/30 hover:bg-primary/5 transition-colors"
            >
              <PhGithubLogo :size="16" />
              <span>GitHub 仓库</span>
              <MIcon name="open_in_new" :size="12" class="text-text-muted" />
            </a>
          </div>
        </div>
      </div>
    </section>

    <!-- Meta Cards -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div
        v-for="card in metaCards"
        :key="card.label"
        class="flex items-start gap-3 rounded-xl border border-surface-border bg-surface-2 px-4 py-3.5"
      >
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-surface">
          <MIcon :name="card.icon" :size="16" class="text-primary" />
        </div>
        <div class="min-w-0">
          <p class="text-xs text-text-muted">{{ card.label }}</p>
          <p class="mt-0.5 text-sm font-medium truncate">{{ card.value }}</p>
        </div>
      </div>
    </div>

    <!-- Changelog Timeline -->
    <section class="rounded-2xl border border-surface-border bg-surface-2 p-6">
      <div class="flex items-center justify-between gap-2 mb-6">
        <div class="flex items-center gap-2">
          <MIcon name="history" :size="18" class="text-primary" />
          <h3 class="text-sm font-semibold">更新记录</h3>
        </div>
        <button
          class="text-xs text-text-muted hover:text-primary cursor-pointer transition-colors"
          @click="versionStore.refresh()"
        >
          检查更新
        </button>
      </div>

      <p v-if="loading" class="text-sm text-text-muted text-center py-8">加载中...</p>

      <div v-else-if="changelog.length === 0" class="text-sm text-text-muted text-center py-8">
        暂无更新记录
      </div>

      <div v-else class="relative">
        <div class="absolute left-[7px] top-3 bottom-3 w-px bg-gradient-to-b from-primary/40 via-surface-border to-transparent" />

        <div
          v-for="(entry, idx) in changelog"
          :key="`${entry.date}-${entry.version}`"
          class="relative pl-8 pb-8 last:pb-0"
        >
          <div
            class="absolute left-0 top-1.5 rounded-full border-2 transition-all"
            :class="idx === 0
              ? 'h-3.5 w-3.5 border-primary bg-primary shadow-[0_0_0_3px] shadow-primary/15'
              : 'h-3 w-3 border-surface-border bg-surface-2'"
          />

          <div class="rounded-xl border border-surface-border/80 bg-surface/40 p-4 hover:border-primary/20 transition-colors">
            <div class="flex flex-wrap items-center gap-2 mb-2">
              <span class="text-xs font-mono text-text-muted">{{ entry.date }}</span>
              <span class="text-[10px] font-mono text-text-muted/70">v{{ entry.version }}</span>
            </div>
            <h4 v-if="entry.title" class="text-sm font-medium text-text-primary">{{ entry.title }}</h4>
            <ul class="space-y-2" :class="entry.title ? 'mt-2.5' : 'mt-1'">
              <li
                v-for="(item, itemIdx) in entry.items"
                :key="`${entry.version}-${itemIdx}`"
                class="flex items-start gap-2 text-xs text-text-secondary leading-relaxed"
              >
                <span
                  class="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium leading-none mt-0.5"
                  :class="tagClass(item.type)"
                >
                  {{ item.type }}
                </span>
                <span>{{ item.text }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <p class="text-center text-xs text-text-muted pb-2">
      Made with care for 飞牛 fnOS
    </p>
  </div>
</template>
