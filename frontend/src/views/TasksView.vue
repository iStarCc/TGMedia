<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useTasksStore, type Task } from "@/stores/tasks";
import { useStatsStore } from "@/stores/stats";
import MIcon from "@/components/common/MIcon.vue";
import FileIcon from "@/components/common/FileIcon.vue";
import ProgressBar from "@/components/common/ProgressBar.vue";
import PaginationBar from "@/components/common/PaginationBar.vue";

const tasksStore = useTasksStore();
const statsStore = useStatsStore();
const statusFilter = ref<string>("");
const searchQuery = ref("");
const currentPage = ref(1);
const pageSize = ref(20);
const selectedIds = ref<Set<string>>(new Set());
const now = ref(Date.now());
let tickTimer: ReturnType<typeof setInterval>;

onMounted(() => {
  tickTimer = setInterval(() => { now.value = Date.now(); }, 1000);
  loadTasks();
});
onUnmounted(() => { clearInterval(tickTimer); });

type SortField = "filename" | "progress" | "created_at" | "";
type SortDir = "asc" | "desc";
const sortField = ref<SortField>("");
const sortDir = ref<SortDir>("desc");

function toggleSort(field: SortField) {
  if (sortField.value === field) {
    sortDir.value = sortDir.value === "asc" ? "desc" : "asc";
  } else {
    sortField.value = field;
    sortDir.value = field === "filename" ? "asc" : "desc";
  }
}

const sortedTasks = computed(() => {
  if (!sortField.value) return tasksStore.tasks;
  const tasks = [...tasksStore.tasks];
  const dir = sortDir.value === "asc" ? 1 : -1;
  return tasks.sort((a: Task, b: Task) => {
    if (sortField.value === "filename") {
      return dir * a.filename.localeCompare(b.filename, "zh-CN");
    }
    if (sortField.value === "progress") {
      const pa = a.file_size > 0 ? a.downloaded / a.file_size : 0;
      const pb = b.file_size > 0 ? b.downloaded / b.file_size : 0;
      return dir * (pa - pb);
    }
    if (sortField.value === "created_at") {
      const ta = new Date(a.created_at).getTime();
      const tb = new Date(b.created_at).getTime();
      return dir * (ta - tb);
    }
    return 0;
  });
});

const allSelected = computed(
  () => tasksStore.tasks.length > 0 && selectedIds.value.size === tasksStore.tasks.length
);

function toggleSelect(id: string) {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id);
  else selectedIds.value.add(id);
}

function toggleAll() {
  if (allSelected.value) {
    selectedIds.value.clear();
  } else {
    selectedIds.value = new Set(tasksStore.tasks.map((t) => t.id));
  }
}

async function batchAction(action: "pause" | "retry") {
  const ids = [...selectedIds.value];
  if (ids.length === 0) return;
  if (action === "pause") await tasksStore.batchPause(ids);
  else if (action === "retry") await tasksStore.batchRetry(ids);
  selectedIds.value.clear();
  loadTasks();
}

function progress(task: { downloaded: number; file_size: number }): number {
  return task.file_size > 0 ? task.downloaded / task.file_size : 0;
}

function downloadDuration(task: { started_at: string | null; updated_at: string; status: string }): number {
  if (!task.started_at) return 0;
  const start = new Date(task.started_at).getTime();
  const end = task.status === "downloading" ? now.value : new Date(task.updated_at).getTime();
  return Math.max(0, (end - start) / 1000);
}

function avgSpeed(task: { file_size: number; started_at: string | null; updated_at: string; status: string }): number {
  const dur = downloadDuration(task);
  if (dur <= 0 || task.file_size <= 0) return 0;
  return task.file_size / dur;
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}秒`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}分${Math.round(seconds % 60)}秒`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}时${m}分`;
}

function formatDate(iso: string): string {
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).replace(/\//g, "-");
}

const showDeleteModal = ref(false);
const deleteTargetId = ref<string | null>(null);
const deleteWithFile = ref(false);
const deleteBatch = ref(false);

function confirmDelete(taskId: string) {
  deleteTargetId.value = taskId;
  deleteWithFile.value = false;
  deleteBatch.value = false;
  showDeleteModal.value = true;
}

function confirmBatchDelete() {
  deleteWithFile.value = false;
  deleteBatch.value = true;
  showDeleteModal.value = true;
}

async function executeDelete() {
  if (deleteBatch.value) {
    await tasksStore.batchDelete([...selectedIds.value], deleteWithFile.value);
    selectedIds.value.clear();
  } else if (deleteTargetId.value) {
    await tasksStore.deleteTask(deleteTargetId.value, deleteWithFile.value);
  }
  showDeleteModal.value = false;
  deleteTargetId.value = null;
  if (tasksStore.tasks.length === 0 && currentPage.value > 1) {
    currentPage.value -= 1;
  }
  loadTasks();
}

function loadTasks() {
  tasksStore.fetchTasks({
    status: statusFilter.value || undefined,
    search: searchQuery.value || undefined,
    page: currentPage.value,
    page_size: pageSize.value,
  });
}

function onPaginationChange() {
  selectedIds.value.clear();
  loadTasks();
}

function applyFilter() {
  currentPage.value = 1;
  selectedIds.value.clear();
  loadTasks();
}

const statusOptions = [
  { value: "", label: "全部" },
  { value: "downloading", label: "下载中" },
  { value: "pending", label: "等待中" },
  { value: "paused", label: "已暂停" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
];

</script>

<template>
  <div class="mx-auto max-w-6xl space-y-4">
    <div class="flex items-center gap-3">
      <div class="flex gap-1 rounded-lg border border-surface-border bg-surface-2 p-0.5">
        <button
          v-for="opt in statusOptions"
          :key="opt.value"
          class="rounded-md px-3 py-1.5 text-xs transition-colors cursor-pointer"
          :class="
            statusFilter === opt.value
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:text-text-primary'
          "
          @click="statusFilter = opt.value; applyFilter()"
        >
          {{ opt.label }}
        </button>
      </div>
      <input
        v-model="searchQuery"
        type="text"
        placeholder="搜索文件名..."
        class="h-8 rounded-lg border border-surface-border bg-surface px-3 text-sm text-text-primary placeholder:text-text-muted outline-none focus:border-primary"
        @input="applyFilter"
      />
    </div>

    <!-- Batch Actions Bar -->
    <div
      v-if="selectedIds.size > 0"
      class="flex items-center gap-3 rounded-lg border border-primary/20 bg-primary/5 px-4 py-2"
    >
      <span class="text-sm">已选 {{ selectedIds.size }} 项</span>
      <button
        class="rounded px-2 py-1 text-xs text-warning hover:bg-warning/10 cursor-pointer transition-colors"
        @click="batchAction('pause')"
      >
        批量暂停
      </button>
      <button
        class="rounded px-2 py-1 text-xs text-primary hover:bg-primary/10 cursor-pointer transition-colors"
        @click="batchAction('retry')"
      >
        批量重试
      </button>
      <button
        class="rounded px-2 py-1 text-xs text-danger hover:bg-danger/10 cursor-pointer transition-colors"
        @click="confirmBatchDelete"
      >
        批量删除
      </button>
      <button
        class="ml-auto text-xs text-text-muted hover:text-text-primary cursor-pointer"
        @click="selectedIds.clear()"
      >
        取消选择
      </button>
    </div>

    <div class="rounded-xl border border-surface-border bg-surface-2 overflow-hidden">
      <div v-if="tasksStore.tasks.length === 0" class="px-5 py-12 text-center text-sm text-text-muted">
        {{ tasksStore.loading ? "加载中..." : "暂无任务" }}
      </div>

      <div v-else class="divide-y divide-surface-border">
        <!-- Header -->
        <div class="flex items-center gap-4 px-5 py-2 text-xs text-text-muted bg-surface/50">
          <button class="cursor-pointer" @click="toggleAll">
            <MIcon :name="allSelected ? 'check_box' : 'check_box_outline_blank'" :size="16" />
          </button>
          <button
            class="flex-1 flex items-center gap-1 cursor-pointer hover:text-text-primary transition-colors text-left"
            @click="toggleSort('filename')"
          >
            文件
            <MIcon
              v-if="sortField === 'filename'"
              :name="sortDir === 'asc' ? 'expand_less' : 'expand_more'"
              :size="12"
              class="text-primary"
            />
          </button>
          <button
            class="w-36 shrink-0 flex items-center gap-1 cursor-pointer hover:text-text-primary transition-colors"
            @click="toggleSort('created_at')"
          >
            时间
            <MIcon
              v-if="sortField === 'created_at'"
              :name="sortDir === 'asc' ? 'expand_less' : 'expand_more'"
              :size="12"
              class="text-primary"
            />
          </button>
          <button
            class="w-72 flex items-center gap-1 cursor-pointer hover:text-text-primary transition-colors"
            @click="toggleSort('progress')"
          >
            进度
            <MIcon
              v-if="sortField === 'progress'"
              :name="sortDir === 'asc' ? 'expand_less' : 'expand_more'"
              :size="12"
              class="text-primary"
            />
          </button>
          <span class="w-20">操作</span>
        </div>

        <div
          v-for="task in sortedTasks"
          :key="task.id"
          class="flex items-center gap-4 px-5 py-3 hover:bg-surface transition-colors"
          :class="{ 'bg-primary/5': selectedIds.has(task.id) }"
        >
          <button class="cursor-pointer shrink-0" @click="toggleSelect(task.id)">
            <MIcon
              :name="selectedIds.has(task.id) ? 'check_box' : 'check_box_outline_blank'"
              :size="16"
              :class="selectedIds.has(task.id) ? 'text-primary' : 'text-text-muted'"
            />
          </button>
          <FileIcon :type="task.media_type" />

          <div class="flex-1 min-w-0">
            <p class="truncate text-sm font-medium">{{ task.filename }}</p>
            <p v-if="task.file_size > 0" class="mt-0.5 text-xs text-text-muted font-mono">
              {{ statsStore.formatBytes(task.downloaded) }} / {{ statsStore.formatBytes(task.file_size) }}
            </p>
          </div>

          <span class="w-36 shrink-0 text-xs text-text-muted font-mono">
            {{ task.created_at ? formatDate(task.created_at) : "—" }}
          </span>

          <div class="w-72 shrink-0 flex flex-col justify-center">
            <div class="mb-1 flex h-[14px] items-center justify-end gap-2">
              <span
                v-if="task.status === 'pending'"
                class="text-[10px] text-text-muted"
              >
                队列中
              </span>
              <template v-else>
                <span
                  v-if="task.speed > 0"
                  class="text-[10px] font-mono text-primary"
                >
                  {{ statsStore.formatBytes(task.speed) }}/s · {{ formatDuration(downloadDuration(task)) }}
                </span>
                <span
                  v-else-if="task.status === 'completed' && avgSpeed(task) > 0"
                  class="text-[10px] font-mono text-text-muted"
                >
                  均速 {{ statsStore.formatBytes(avgSpeed(task)) }}/s · {{ formatDuration(downloadDuration(task)) }}
                </span>
                <span
                  v-else-if="task.status === 'completed' && downloadDuration(task) > 0"
                  class="text-[10px] font-mono text-text-muted"
                >
                  耗时 {{ formatDuration(downloadDuration(task)) }}
                </span>
                <span class="text-[10px] font-mono text-text-muted">
                  {{ Math.round(progress(task) * 100) }}%
                </span>
              </template>
            </div>
            <ProgressBar :progress="progress(task)" :status="task.status" />
            <div class="mt-1 h-[14px]" aria-hidden="true" />
          </div>

          <div class="flex items-center gap-1 shrink-0 w-20">
            <button
              v-if="task.status === 'downloading'"
              class="rounded-md p-1.5 text-text-muted hover:bg-surface-border hover:text-warning cursor-pointer transition-colors"
              title="暂停"
              @click="tasksStore.pauseTask(task.id)"
            >
              <MIcon name="pause" :size="16" />
            </button>
            <button
              v-if="task.status === 'paused'"
              class="rounded-md p-1.5 text-text-muted hover:bg-surface-border hover:text-primary cursor-pointer transition-colors"
              title="恢复"
              @click="tasksStore.resumeTask(task.id)"
            >
              <MIcon name="play_arrow" :size="16" />
            </button>
            <button
              v-if="['failed', 'completed', 'paused'].includes(task.status)"
              class="rounded-md p-1.5 text-text-muted hover:bg-surface-border hover:text-primary cursor-pointer transition-colors"
              :title="task.status === 'completed' ? '重新下载' : '重试'"
              @click="tasksStore.retryTask(task.id)"
            >
              <MIcon name="replay" :size="16" />
            </button>
            <button
              class="rounded-md p-1.5 text-text-muted hover:bg-surface-border hover:text-danger cursor-pointer transition-colors"
              title="删除"
              @click="confirmDelete(task.id)"
            >
              <MIcon name="delete" :size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <PaginationBar
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="tasksStore.total"
      unit="任务"
      @change="onPaginationChange"
    />

    <!-- 删除确认弹窗 -->
    <Teleport to="body">
      <div
        v-if="showDeleteModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="showDeleteModal = false"
      >
        <div class="w-full max-w-sm rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl">
          <h2 class="text-base font-semibold">确认删除</h2>
          <p class="mt-2 text-sm text-text-secondary">
            {{ deleteBatch ? `确定删除选中的 ${selectedIds.size} 个任务吗？` : '确定删除此任务吗？' }}
          </p>

          <label class="mt-4 flex items-center gap-2 cursor-pointer">
            <input
              v-model="deleteWithFile"
              type="checkbox"
              class="h-4 w-4 rounded accent-danger cursor-pointer"
            />
            <span class="text-sm text-text-secondary">同时删除已下载的文件</span>
          </label>
          <p v-if="deleteWithFile" class="mt-1 ml-6 text-xs text-danger">
            文件删除后无法恢复
          </p>

          <div class="mt-5 flex justify-end gap-2">
            <button
              class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
              @click="showDeleteModal = false"
            >
              取消
            </button>
            <button
              class="rounded-lg bg-danger px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-danger/80 transition-colors"
              @click="executeDelete"
            >
              {{ deleteWithFile ? '删除任务和文件' : '仅删除任务' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
