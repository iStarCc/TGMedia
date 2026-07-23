<script setup lang="ts">
import { onMounted } from "vue";
import { useStatsStore } from "@/stores/stats";
import MIcon from "@/components/common/MIcon.vue";
import StatsCard from "@/components/dashboard/StatsCard.vue";
import SpeedChart from "@/components/dashboard/SpeedChart.vue";
import RecentTasks from "@/components/dashboard/RecentTasks.vue";

const statsStore = useStatsStore();

onMounted(() => {
  statsStore.fetchStats();
});
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-5">
    <div class="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <StatsCard
        label="下载中"
        :value="statsStore.stats.downloading"
        icon="download"
        color="bg-info/10 text-info"
      />
      <StatsCard
        label="已完成"
        :value="statsStore.stats.completed"
        icon="check_circle"
        color="bg-primary/10 text-primary"
      />
      <StatsCard
        label="总大小"
        :value="statsStore.formattedTotalSize"
        icon="storage"
        color="bg-purple-500/10 text-purple-500"
      />
      <StatsCard
        label="当前速度"
        :value="statsStore.formattedSpeed"
        icon="bolt"
        color="bg-amber-500/10 text-amber-500"
      />
    </div>

    <SpeedChart />

    <div class="grid grid-cols-1 gap-4 lg:grid-cols-3 items-stretch">
      <div class="lg:col-span-2 min-h-0">
        <RecentTasks />
      </div>

      <div class="rounded-xl border border-surface-border bg-surface-2 p-4">
        <h3 class="text-sm font-medium mb-4">概览</h3>
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="flex h-6 w-6 items-center justify-center rounded-md bg-purple-500/10">
                <MIcon name="person" :size="12" class="text-purple-500" />
              </div>
              <span class="text-xs text-text-secondary">账号</span>
            </div>
            <span class="text-xs font-mono font-medium">{{ statsStore.stats.account_count }}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10">
                <MIcon name="rss_feed" :size="12" class="text-primary" />
              </div>
              <span class="text-xs text-text-secondary">订阅源</span>
            </div>
            <span class="text-xs font-mono font-medium">{{ statsStore.stats.channel_count }}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="flex h-6 w-6 items-center justify-center rounded-md bg-info/10">
                <MIcon name="queue" :size="12" class="text-info" />
              </div>
              <span class="text-xs text-text-secondary">等待中</span>
            </div>
            <span class="text-xs font-mono font-medium">{{ statsStore.stats.pending }}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="flex h-6 w-6 items-center justify-center rounded-md bg-warning/10">
                <MIcon name="pause" :size="12" class="text-warning" />
              </div>
              <span class="text-xs text-text-secondary">已暂停</span>
            </div>
            <span class="text-xs font-mono font-medium text-warning">{{ statsStore.stats.paused }}</span>
          </div>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <div class="flex h-6 w-6 items-center justify-center rounded-md bg-danger/10">
                <MIcon name="warning" :size="12" class="text-danger" />
              </div>
              <span class="text-xs text-text-secondary">失败</span>
            </div>
            <span class="text-xs font-mono font-medium text-danger">{{ statsStore.stats.failed }}</span>
          </div>
          <div class="h-px bg-surface-border" />
          <div class="flex items-center justify-between">
            <span class="text-xs text-text-secondary">总任务</span>
            <span class="text-xs font-mono font-medium">{{ statsStore.stats.total_tasks }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
