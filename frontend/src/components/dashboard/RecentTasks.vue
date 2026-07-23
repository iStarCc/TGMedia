<script setup lang="ts">
import { onMounted } from "vue";
import { useTasksStore } from "@/stores/tasks";
import { useStatsStore } from "@/stores/stats";
import FileIcon from "@/components/common/FileIcon.vue";
import ProgressBar from "@/components/common/ProgressBar.vue";

const tasksStore = useTasksStore();
const statsStore = useStatsStore();

const statusLabels: Record<string, string> = {
  downloading: "下载中",
  completed: "已完成",
  paused: "已暂停",
  failed: "失败",
  pending: "等待中",
};

function progress(task: { downloaded: number; file_size: number }): number {
  return task.file_size > 0 ? task.downloaded / task.file_size : 0;
}

onMounted(() => {
  tasksStore.fetchTasks({ page: 1 });
});
</script>

<template>
  <div class="rounded-xl border border-surface-border bg-surface-2 h-full flex flex-col">
    <div class="flex items-center justify-between border-b border-surface-border px-4 py-2.5">
      <h3 class="text-sm font-medium">活跃任务</h3>
      <RouterLink to="/tasks" class="text-[10px] text-primary cursor-pointer hover:underline">
        查看全部
      </RouterLink>
    </div>

    <div v-if="tasksStore.tasks.length === 0" class="flex-1 flex items-center justify-center px-4 text-xs text-text-muted">
      暂无下载任务
    </div>

    <div v-else class="flex-1 divide-y divide-surface-border">
      <div
        v-for="task in tasksStore.tasks.slice(0, 5)"
        :key="task.id"
        class="flex items-center gap-2.5 px-4 py-2.5"
      >
        <FileIcon :type="task.media_type" />
        <div class="flex-1 min-w-0">
          <p class="truncate text-xs">{{ task.filename }}</p>
          <div class="mt-1">
            <ProgressBar :progress="progress(task)" :status="task.status" />
          </div>
        </div>
        <div class="flex flex-col items-end gap-0.5 shrink-0">
          <span
            class="text-[10px] font-mono"
            :class="{
              'text-primary': task.status === 'downloading',
              'text-text-muted': task.status === 'completed',
              'text-warning': task.status === 'paused',
              'text-danger': task.status === 'failed',
            }"
          >
            {{ task.status === 'downloading' ? `${Math.round(progress(task) * 100)}%` : statusLabels[task.status] || task.status }}
          </span>
          <span v-if="task.speed > 0" class="text-[10px] font-mono text-text-muted">
            {{ statsStore.formatBytes(task.speed) }}/s
          </span>
        </div>
      </div>
    </div>
  </div>
</template>
