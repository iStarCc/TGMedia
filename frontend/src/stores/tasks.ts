import { defineStore } from "pinia";
import { ref } from "vue";
import { useWebSocket } from "@/composables/useWebSocket";
import { useStatsStore } from "@/stores/stats";
import { apiFetch } from "@/utils/api";
import { readApiError } from "@/utils/apiError";

export interface Task {
  id: string;
  channel_id: number | null;
  message_id: number | null;
  filename: string;
  file_size: number;
  downloaded: number;
  media_type: string;
  status: string;
  speed: number;
  error: string | null;
  file_path: string | null;
  started_at: string | null;
  created_at: string;
  updated_at: string;
}

export const useTasksStore = defineStore("tasks", () => {
  const tasks = ref<Task[]>([]);
  const total = ref(0);
  const loading = ref(false);

  const { on } = useWebSocket();
  const progressSnapshot = new Map<string, { bytes: number; at: number }>();

  function resolveSpeed(taskId: string, downloaded: number, speed: number): number {
    const snap = progressSnapshot.get(taskId);
    const now = Date.now();
    if (!snap || snap.bytes !== downloaded) {
      progressSnapshot.set(taskId, { bytes: downloaded, at: now });
      return speed;
    }
    if (now - snap.at > 2000) return 0;
    return speed;
  }

  function clearProgressSnapshot(taskId: string) {
    progressSnapshot.delete(taskId);
  }

  let lastFetchParams: {
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = { page: 1, page_size: 20 };

  async function fetchTasks(params?: {
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  }) {
    loading.value = true;
    lastFetchParams = { ...lastFetchParams, ...params };
    try {
      const qs = new URLSearchParams();
      if (lastFetchParams.status) qs.set("status", lastFetchParams.status);
      if (lastFetchParams.search) qs.set("search", lastFetchParams.search);
      if (lastFetchParams.page) qs.set("page", String(lastFetchParams.page));
      if (lastFetchParams.page_size !== undefined) {
        qs.set("page_size", String(lastFetchParams.page_size));
      }
      const res = await apiFetch(`/api/tasks?${qs}`);
      if (res.ok) {
        const data = await res.json();
        tasks.value = data.tasks;
        total.value = data.total;
      }
    } finally {
      loading.value = false;
    }
  }

  async function pauseTask(taskId: string) {
    const res = await apiFetch(`/api/tasks/${taskId}/pause`, { method: "POST" });
    if (!res.ok) throw await readApiError(res);
  }

  async function resumeTask(taskId: string) {
    const res = await apiFetch(`/api/tasks/${taskId}/resume`, { method: "POST" });
    if (!res.ok) throw await readApiError(res);
    await fetchTasks(lastFetchParams);
  }

  async function deleteTask(taskId: string, deleteFile = false) {
    const statsStore = useStatsStore();
    const task = tasks.value.find((t) => t.id === taskId);
    const qs = deleteFile ? "?delete_file=true" : "";
    const res = await apiFetch(`/api/tasks/${taskId}${qs}`, { method: "DELETE" });
    if (!res.ok) throw await readApiError(res);
    tasks.value = tasks.value.filter((t) => t.id !== taskId);
    total.value--;
    if (task) statsStore.adjustTaskCount(task.status, -1);
  }

  async function retryTask(taskId: string) {
    const res = await apiFetch(`/api/tasks/${taskId}/retry`, { method: "POST" });
    if (!res.ok) throw await readApiError(res);
    await fetchTasks(lastFetchParams);
  }

  async function batchPause(taskIds: string[]) {
    const res = await apiFetch("/api/tasks/batch/pause", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taskIds),
    });
    if (!res.ok) throw await readApiError(res);
    for (const id of taskIds) {
      const t = tasks.value.find((t) => t.id === id);
      if (t) t.status = "paused";
    }
  }

  async function batchDelete(taskIds: string[], deleteFile = false) {
    const statsStore = useStatsStore();
    const removed = tasks.value.filter((t) => taskIds.includes(t.id));
    const res = await apiFetch("/api/tasks/batch/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task_ids: taskIds, delete_file: deleteFile }),
    });
    if (!res.ok) throw await readApiError(res);
    tasks.value = tasks.value.filter((t) => !taskIds.includes(t.id));
    total.value -= taskIds.length;
    for (const task of removed) {
      statsStore.adjustTaskCount(task.status, -1);
    }
  }

  async function batchRetry(taskIds: string[]) {
    const res = await apiFetch("/api/tasks/batch/retry", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(taskIds),
    });
    if (!res.ok) throw await readApiError(res);
    await fetchTasks(lastFetchParams);
  }

  on("task:progress", (data) => {
    const taskId = data.task_id as string;
    const task = tasks.value.find((t) => t.id === taskId);
    if (task) {
      if (task.status !== "downloading") {
        task.started_at = new Date().toISOString();
      }
      const downloaded = data.downloaded as number;
      task.downloaded = downloaded;
      task.file_size = data.file_size as number;
      task.speed = resolveSpeed(taskId, downloaded, data.speed as number);
      task.status = "downloading";
    }
  });

  on("task:created", (data) => {
    tasks.value.unshift({
      id: data.task_id as string,
      channel_id: null,
      message_id: null,
      filename: data.filename as string,
      file_size: data.file_size as number,
      downloaded: 0,
      media_type: data.media_type as string,
      status: "pending",
      speed: 0,
      error: null,
      file_path: null,
      started_at: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    });
    total.value++;
  });

  on("task:completed", (data) => {
    const taskId = data.task_id as string;
    clearProgressSnapshot(taskId);
    const task = tasks.value.find((t) => t.id === taskId);
    if (task) {
      task.status = "completed";
      task.downloaded = task.file_size;
      task.speed = 0;
      if (data.started_at) task.started_at = data.started_at as string;
      if (data.updated_at) task.updated_at = data.updated_at as string;
    }
  });

  on("task:failed", (data) => {
    clearProgressSnapshot(data.task_id as string);
    const task = tasks.value.find((t) => t.id === data.task_id);
    if (task) {
      task.status = "failed";
      task.error = data.error as string;
      task.speed = 0;
    }
  });

  on("task:paused", (data) => {
    clearProgressSnapshot(data.task_id as string);
    const task = tasks.value.find((t) => t.id === data.task_id);
    if (task) {
      task.status = "paused";
      task.speed = 0;
    }
  });

  return {
    tasks, total, loading,
    fetchTasks, pauseTask, resumeTask, deleteTask, retryTask,
    batchPause, batchDelete, batchRetry,
  };
});
