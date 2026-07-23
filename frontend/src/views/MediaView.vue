<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import MIcon from "@/components/common/MIcon.vue";
import { useStatsStore } from "@/stores/stats";
import { apiFetch, apiUrl } from "@/utils/api";
import FileIcon from "@/components/common/FileIcon.vue";
import PaginationBar from "@/components/common/PaginationBar.vue";

const statsStore = useStatsStore();

interface MediaFile {
  id: number;
  filename: string;
  file_path: string;
  file_size: number;
  media_type: string;
  created_at: string;
}

interface MediaMessage {
  message_id: number;
  channel_id: number | null;
  channel_title: string;
  media_type: string;
  filename: string;
  file_size: number;
  text: string;
  date: string;
}

const files = ref<MediaFile[]>([]);
const total = ref(0);
const loading = ref(false);
const activeType = ref("all");
const searchQuery = ref("");
const sortField = ref<"filename" | "file_size" | "created_at">("created_at");
const sortOrder = ref<"asc" | "desc">("desc");
const currentPage = ref(1);
const pageSize = ref(20);
const previewFile = ref<MediaFile | null>(null);
const textContent = ref("");
const messageFile = ref<MediaFile | null>(null);
const messageInfo = ref<MediaMessage | null>(null);
const messageLoading = ref(false);
const messageError = ref("");
let searchTimer: ReturnType<typeof setTimeout>;

const typeOptions = [
  { value: "all", label: "全部" },
  { value: "video", label: "视频" },
  { value: "photo", label: "图片" },
  { value: "document", label: "文档" },
  { value: "audio", label: "音频" },
];

watch(searchQuery, () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    currentPage.value = 1;
    fetchMedia();
  }, 300);
});

const videoExts = ["mp4", "mkv", "avi", "webm", "mov"];
const audioExts = ["mp3", "flac", "ogg", "wav", "aac", "m4a"];
const imageExts = ["jpg", "jpeg", "png", "gif", "webp", "svg"];
const textExts = ["txt", "log", "md", "json", "xml", "csv", "html", "css", "js"];

function getExt(filename: string): string {
  return filename.includes(".") ? filename.split(".").pop()!.toLowerCase() : "";
}

const previewType = computed(() => {
  if (!previewFile.value) return "none";
  const ext = getExt(previewFile.value.filename);
  if (videoExts.includes(ext)) return "video";
  if (audioExts.includes(ext)) return "audio";
  if (imageExts.includes(ext)) return "image";
  if (textExts.includes(ext)) return "text";
  if (ext === "pdf") return "pdf";
  return "none";
});

function canPreview(file: MediaFile): boolean {
  const ext = getExt(file.filename);
  return [...videoExts, ...audioExts, ...imageExts, ...textExts, "pdf"].includes(ext);
}

async function openPreview(file: MediaFile) {
  previewFile.value = file;
  textContent.value = "";
  const ext = getExt(file.filename);
  if (textExts.includes(ext)) {
    const res = await apiFetch(`/api/media/${file.id}/preview`);
    if (res.ok) textContent.value = await res.text();
  }
}

function closePreview() {
  previewFile.value = null;
  textContent.value = "";
}

async function openMessageInfo(file: MediaFile) {
  messageFile.value = file;
  messageInfo.value = null;
  messageError.value = "";
  messageLoading.value = true;
  try {
    const res = await apiFetch(`/api/media/${file.id}/message`);
    if (res.ok) {
      messageInfo.value = await res.json();
    } else {
      const err = await res.json().catch(() => null);
      messageError.value = (err as { detail?: string })?.detail || "无法获取消息信息";
    }
  } catch {
    messageError.value = "网络错误，请稍后重试";
  } finally {
    messageLoading.value = false;
  }
}

function closeMessageInfo() {
  messageFile.value = null;
  messageInfo.value = null;
  messageError.value = "";
}

function formatMessageDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso.endsWith("Z") ? iso : iso + "Z");
  return d.toLocaleString("zh-CN", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).replace(/\//g, "-");
}

async function fetchMedia() {
  loading.value = true;
  try {
    const qs = new URLSearchParams();
    if (activeType.value !== "all") qs.set("media_type", activeType.value);
    if (searchQuery.value.trim()) qs.set("search", searchQuery.value.trim());
    qs.set("sort", sortField.value);
    qs.set("order", sortOrder.value);
    qs.set("page", String(currentPage.value));
    qs.set("page_size", String(pageSize.value));
    const res = await apiFetch(`/api/media?${qs}`);
    if (res.ok) {
      const data = await res.json();
      files.value = data.files;
      total.value = data.total;
    }
  } finally {
    loading.value = false;
  }
}

async function deleteFile(id: number) {
  await apiFetch(`/api/media/${id}`, { method: "DELETE" });
  files.value = files.value.filter((f) => f.id !== id);
  total.value--;
  if (files.value.length === 0 && currentPage.value > 1) {
    currentPage.value -= 1;
  }
  fetchMedia();
}

function switchType(type: string) {
  activeType.value = type;
  currentPage.value = 1;
  fetchMedia();
}

function toggleSort(field: "filename" | "file_size" | "created_at") {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === "asc" ? "desc" : "asc";
  } else {
    sortField.value = field;
    sortOrder.value = field === "filename" ? "asc" : "desc";
  }
  currentPage.value = 1;
  fetchMedia();
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
    second: "2-digit",
    hour12: false,
  }).replace(/\//g, "-");
}

onMounted(fetchMedia);
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-4">
    <div class="flex items-center gap-2">
      <div class="flex gap-1 rounded-lg border border-surface-border bg-surface-2 p-0.5">
        <button
          v-for="opt in typeOptions"
          :key="opt.value"
          class="rounded-md px-2.5 py-1 text-[11px] transition-colors cursor-pointer"
          :class="
            activeType === opt.value
              ? 'bg-primary text-white'
              : 'text-text-secondary hover:text-text-primary'
          "
          @click="switchType(opt.value)"
        >
          {{ opt.label }}
        </button>
      </div>
      <div class="relative">
        <MIcon name="search" :size="14" class="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-muted" />
        <input
          v-model="searchQuery"
          type="text"
          placeholder="搜索..."
          class="rounded-lg border border-surface-border bg-surface pl-8 pr-3 py-1 text-[11px] outline-none focus:border-primary w-36 transition-colors"
        />
      </div>
      <div class="flex items-center gap-0.5 ml-auto">
        <button
          class="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] cursor-pointer transition-colors"
          :class="sortField === 'filename' ? 'text-primary' : 'text-text-muted hover:text-text-secondary'"
          @click="toggleSort('filename')"
        >
          名称
          <MIcon v-if="sortField === 'filename'" :name="sortOrder === 'asc' ? 'expand_less' : 'expand_more'" :size="12" />
        </button>
        <button
          class="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] cursor-pointer transition-colors"
          :class="sortField === 'file_size' ? 'text-primary' : 'text-text-muted hover:text-text-secondary'"
          @click="toggleSort('file_size')"
        >
          大小
          <MIcon v-if="sortField === 'file_size'" :name="sortOrder === 'asc' ? 'expand_less' : 'expand_more'" :size="12" />
        </button>
        <button
          class="flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[11px] cursor-pointer transition-colors"
          :class="sortField === 'created_at' ? 'text-primary' : 'text-text-muted hover:text-text-secondary'"
          @click="toggleSort('created_at')"
        >
          日期
          <MIcon v-if="sortField === 'created_at'" :name="sortOrder === 'asc' ? 'expand_less' : 'expand_more'" :size="12" />
        </button>
      </div>
    </div>

    <div v-if="files.length === 0" class="rounded-xl border border-surface-border bg-surface-2 px-5 py-12 text-center text-sm text-text-muted">
      {{ loading ? "加载中..." : "暂无媒体文件" }}
    </div>

    <div v-else class="rounded-xl border border-surface-border bg-surface-2 overflow-hidden divide-y divide-surface-border">
      <div
        v-for="file in files"
        :key="file.id"
        class="flex items-center gap-4 px-5 py-3 hover:bg-surface transition-colors"
      >
        <FileIcon :type="file.media_type" />
        <div class="flex-1 min-w-0">
          <p class="truncate text-sm">{{ file.filename }}</p>
          <p class="text-xs text-text-muted mt-0.5">
            {{ statsStore.formatBytes(file.file_size) }}
          </p>
        </div>
        <span class="text-xs text-text-muted shrink-0">
          {{ formatDate(file.created_at) }}
        </span>
        <button
          v-if="canPreview(file)"
          class="rounded-md p-1.5 text-text-muted hover:text-info cursor-pointer transition-colors"
          title="预览"
          @click="openPreview(file)"
        >
          <MIcon name="visibility" :size="16" />
        </button>
        <button
          class="rounded-md p-1.5 text-text-muted hover:text-info cursor-pointer transition-colors"
          title="消息信息"
          @click="openMessageInfo(file)"
        >
          <MIcon name="info" :size="16" />
        </button>
        <a
          :href="apiUrl(`/api/media/${file.id}/download`)"
          class="rounded-md p-1.5 text-text-muted hover:text-primary cursor-pointer transition-colors"
          title="下载"
        >
          <MIcon name="download" :size="16" />
        </a>
        <button
          class="rounded-md p-1.5 text-text-muted hover:text-danger cursor-pointer transition-colors"
          title="删除"
          @click="deleteFile(file.id)"
        >
          <MIcon name="delete" :size="16" />
        </button>
      </div>
    </div>

    <PaginationBar
      v-model:current-page="currentPage"
      v-model:page-size="pageSize"
      :total="total"
      unit="文件"
      @change="fetchMedia"
    />

    <!-- 预览弹窗 -->
    <Teleport to="body">
      <div
        v-if="previewFile"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        @click.self="closePreview"
      >
        <div class="relative w-full max-w-4xl max-h-[85vh] rounded-xl border border-surface-border bg-surface-2 shadow-2xl flex flex-col overflow-hidden">
          <div class="flex items-center justify-between px-5 py-3 border-b border-surface-border shrink-0">
            <div class="min-w-0">
              <p class="text-sm font-medium truncate">{{ previewFile.filename }}</p>
              <p class="text-xs text-text-muted">{{ statsStore.formatBytes(previewFile.file_size) }}</p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <a
                :href="apiUrl(`/api/media/${previewFile.id}/download`)"
                class="rounded-md p-1.5 text-text-muted hover:text-primary cursor-pointer transition-colors"
                title="下载"
              >
                <MIcon name="download" :size="16" />
              </a>
              <button
                class="rounded-md p-1.5 text-text-muted hover:text-text-primary cursor-pointer transition-colors"
                @click="closePreview"
              >
                <MIcon name="close" :size="16" />
              </button>
            </div>
          </div>

          <div class="flex-1 overflow-auto flex items-center justify-center p-4">
            <video
              v-if="previewType === 'video'"
              :src="apiUrl(`/api/media/${previewFile.id}/preview`)"
              controls
              class="max-w-full max-h-[70vh] rounded-lg"
            />
            <audio
              v-else-if="previewType === 'audio'"
              :src="apiUrl(`/api/media/${previewFile.id}/preview`)"
              controls
              class="w-full max-w-md"
            />
            <img
              v-else-if="previewType === 'image'"
              :src="apiUrl(`/api/media/${previewFile.id}/preview`)"
              class="max-w-full max-h-[70vh] rounded-lg object-contain"
            />
            <iframe
              v-else-if="previewType === 'pdf'"
              :src="apiUrl(`/api/media/${previewFile.id}/preview`)"
              class="w-full h-[70vh] rounded-lg border-0"
            />
            <pre
              v-else-if="previewType === 'text'"
              class="w-full max-h-[70vh] overflow-auto rounded-lg bg-surface p-4 text-xs font-mono text-text-primary whitespace-pre-wrap break-all"
            >{{ textContent }}</pre>
            <p v-else class="text-sm text-text-muted">不支持预览此文件类型</p>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 消息信息弹窗 -->
    <Teleport to="body">
      <div
        v-if="messageFile"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        @click.self="closeMessageInfo"
      >
        <div class="w-full max-w-lg rounded-xl border border-surface-border bg-surface-2 shadow-2xl overflow-hidden">
          <div class="flex items-center justify-between px-5 py-3 border-b border-surface-border">
            <div class="min-w-0">
              <p class="text-sm font-medium">消息信息</p>
              <p class="text-xs text-text-muted truncate">{{ messageFile.filename }}</p>
            </div>
            <button
              class="rounded-md p-1.5 text-text-muted hover:text-text-primary cursor-pointer transition-colors"
              @click="closeMessageInfo"
            >
              <MIcon name="close" :size="16" />
            </button>
          </div>

          <div class="px-5 py-4 text-xs space-y-3 max-h-[60vh] overflow-y-auto">
            <p v-if="messageLoading" class="text-text-muted text-center py-6">加载中...</p>
            <p v-else-if="messageError" class="text-danger text-center py-6">{{ messageError }}</p>
            <template v-else-if="messageInfo">
              <div v-if="messageInfo.channel_title" class="flex gap-4">
                <span class="text-text-muted shrink-0 w-16">频道</span>
                <span class="break-all">{{ messageInfo.channel_title }}</span>
              </div>
              <div class="flex gap-4">
                <span class="text-text-muted shrink-0 w-16">文件名</span>
                <span class="break-all">{{ messageInfo.filename }}</span>
              </div>
              <div class="flex gap-4">
                <span class="text-text-muted shrink-0 w-16">大小</span>
                <span>{{ messageInfo.file_size ? statsStore.formatBytes(messageInfo.file_size) : "未知" }}</span>
              </div>
              <div class="flex gap-4">
                <span class="text-text-muted shrink-0 w-16">类型</span>
                <span>{{ messageInfo.media_type }}</span>
              </div>
              <div class="flex gap-4">
                <span class="text-text-muted shrink-0 w-16">消息 ID</span>
                <span class="font-mono">{{ messageInfo.message_id }}</span>
              </div>
              <div v-if="messageInfo.date" class="flex gap-4">
                <span class="text-text-muted shrink-0 w-16">时间</span>
                <span>{{ formatMessageDate(messageInfo.date) }}</span>
              </div>
              <div v-if="messageInfo.text" class="flex gap-4">
                <span class="text-text-muted shrink-0 w-16">描述</span>
                <span class="whitespace-pre-wrap break-all">{{ messageInfo.text }}</span>
              </div>
              <p v-if="!messageInfo.text" class="text-text-muted">该消息无描述文本</p>
            </template>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
