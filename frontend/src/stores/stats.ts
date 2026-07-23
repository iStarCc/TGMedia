import { defineStore } from "pinia";
import { computed, onMounted, ref } from "vue";
import { useWebSocket } from "@/composables/useWebSocket";
import { apiFetch } from "@/utils/api";

interface Stats {
  total_tasks: number;
  downloading: number;
  completed: number;
  failed: number;
  paused: number;
  pending: number;
  total_size: number;
  current_speed: number;
  channel_count: number;
  account_count: number;
}

const defaultStats: Stats = {
  total_tasks: 0,
  downloading: 0,
  completed: 0,
  failed: 0,
  paused: 0,
  pending: 0,
  total_size: 0,
  current_speed: 0,
  channel_count: 0,
  account_count: 0,
};

export const useStatsStore = defineStore("stats", () => {
  const stats = ref<Stats>({ ...defaultStats });
  const { connected, on } = useWebSocket();

  async function fetchStats() {
    try {
      const res = await apiFetch("/api/stats");
      if (res.ok) stats.value = await res.json();
    } catch {
      /* network error */
    }
  }

  function formatBytes(bytes: number): string {
    if (bytes === 0) return "0 B";
    const units = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / 1024 ** i).toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
  }

  const formattedSpeed = computed(() => `${formatBytes(stats.value.current_speed)}/s`);
  const formattedTotalSize = computed(() => formatBytes(stats.value.total_size));

  on("stats:update", (data) => {
    Object.assign(stats.value, data);
  });

  on("task:created", () => fetchStats());
  on("task:completed", () => fetchStats());
  on("task:failed", () => fetchStats());

  function adjustTaskCount(status: string, delta: number) {
    const statusKey = status as keyof Pick<
      Stats,
      "downloading" | "pending" | "completed" | "failed" | "paused"
    >;
    if (statusKey in stats.value && typeof stats.value[statusKey] === "number") {
      stats.value[statusKey] = Math.max(0, stats.value[statusKey] + delta);
    }
    stats.value.total_tasks = Math.max(0, stats.value.total_tasks + delta);
  }

  onMounted(fetchStats);

  return {
    stats,
    connected,
    formattedSpeed,
    formattedTotalSize,
    formatBytes,
    fetchStats,
    adjustTaskCount,
  };
});
