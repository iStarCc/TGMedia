<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed, nextTick } from "vue";
import MIcon from "@/components/common/MIcon.vue";
import { useChannelsStore, type Channel } from "@/stores/channels";
import { useAccountsStore } from "@/stores/accounts";
import { apiFetch, apiUrl } from "@/utils/api";
import { useStatsStore } from "@/stores/stats";

interface AppSettings {
  allowed_extensions: string[];
  [key: string]: unknown;
}

interface SearchResult {
  message_id: number;
  channel_id: number;
  channel_title: string;
  date: string;
  media_type: string;
  filename: string;
  file_size: number;
  text: string;
  downloaded?: boolean;
}

const channelsStore = useChannelsStore();
const accountsStore = useAccountsStore();
const statsStore = useStatsStore();
const globalSettings = ref<AppSettings>({ allowed_extensions: [] });

const showAddModal = ref(false);
const showConfigModal = ref(false);
const configChannel = ref<Channel | null>(null);
const cfgFilterType = ref("all");
const cfgMaxSize = ref(0);
const cfgMaxSizeInput = ref(0);
const cfgMaxSizeUnit = ref<'MB' | 'GB'>('MB');
const cfgExtensions = ref<string[]>([]);
const cfgExtUseGlobal = ref(true);
const cfgNewExt = ref("");
const cfgDownloadPath = ref("");
const cfgPathUseGlobal = ref(true);
const cfgSyncLimit = ref(0);
const cfgSyncUseGlobal = ref(true);
const newLink = ref("");
const selectedAccountId = ref<number | null>(null);
const addError = ref("");
const adding = ref(false);
const syncing = ref<number | null>(null);

interface SyncMessage {
  message_id: number;
  date: string;
  media_type: string;
  filename: string;
  file_size: number;
  text: string;
  downloaded?: boolean;
}
const showSyncModal = ref(false);
const syncMessages = ref<SyncMessage[]>([]);
const syncChannelId = ref<number | null>(null);
const syncChannelTitle = ref("");
const selectedMsgIds = ref<Set<number>>(new Set());
const downloading = ref(false);
const confirmDeleteId = ref<number | null>(null);
const filterAccountId = ref<number | null>(null);
const photoErrors = ref<Set<number>>(new Set());
const expandedMsgIds = ref<Set<number>>(new Set());

// 搜索相关状态
const showSearchModal = ref(false);
const searchKeyword = ref("");
const searchMediaType = ref("all");
const searchAccountId = ref<number | null>(null);
const searchChannelId = ref<number | null>(null);
const searchLimitChoice = ref("50");
const searchCustomLimit = ref(200);
const searchExtensions = ref<string[]>([]);
const searchNewExt = ref("");
const searchResults = ref<SearchResult[]>([]);
const searchCursors = ref<Record<string, number>>({});
const searchHasMore = ref(false);
const searching = ref(false);
const searchLoadingMore = ref(false);
const selectedSearchIds = ref<Set<string>>(new Set());
const searchDownloading = ref(false);
const searchPerformed = ref(false);
const expandedSearchIds = ref<Set<string>>(new Set());
const searchSentinelRef = ref<HTMLElement | null>(null);
let searchObserver: IntersectionObserver | null = null;

function toggleDetail(id: number) {
  if (expandedMsgIds.value.has(id)) {
    expandedMsgIds.value.delete(id);
  } else {
    expandedMsgIds.value.add(id);
  }
  expandedMsgIds.value = new Set(expandedMsgIds.value);
}

const filteredChannels = computed(() => {
  if (!filterAccountId.value) return channelsStore.channels;
  return channelsStore.channels.filter(c => c.account_id === filterAccountId.value);
});

async function handleAdd() {
  if (!newLink.value.trim() || !selectedAccountId.value) return;
  adding.value = true;
  addError.value = "";
  try {
    await channelsStore.addChannel(newLink.value.trim(), selectedAccountId.value);
    newLink.value = "";
    showAddModal.value = false;
    photoErrors.value = new Set();
  } catch (e: unknown) {
    addError.value = e instanceof Error ? e.message : "添加失败";
  } finally {
    adding.value = false;
  }
}

async function toggleAutoDownload(channel: { id: number; auto_download: boolean }) {
  await channelsStore.updateChannel(channel.id, {
    auto_download: !channel.auto_download,
  });
}

function bytesToDisplay(bytes: number): { value: number; unit: 'MB' | 'GB' } {
  if (bytes >= 1024 * 1024 * 1024 && bytes % (1024 * 1024 * 1024) === 0) {
    return { value: bytes / (1024 * 1024 * 1024), unit: 'GB' };
  }
  return { value: bytes / (1024 * 1024), unit: 'MB' };
}

function displayToBytes(value: number, unit: 'MB' | 'GB'): number {
  return unit === 'GB' ? value * 1024 * 1024 * 1024 : value * 1024 * 1024;
}

function openConfig(channel: Channel) {
  configChannel.value = channel;
  cfgFilterType.value = channel.filter_type;
  cfgMaxSize.value = channel.max_file_size;
  if (channel.max_file_size > 0) {
    const { value, unit } = bytesToDisplay(channel.max_file_size);
    cfgMaxSizeInput.value = value;
    cfgMaxSizeUnit.value = unit;
  } else {
    cfgMaxSizeInput.value = 0;
    cfgMaxSizeUnit.value = 'MB';
  }
  cfgDownloadPath.value = channel.download_path || "";
  cfgPathUseGlobal.value = !channel.download_path;
  cfgSyncLimit.value = channel.sync_limit || 0;
  cfgSyncUseGlobal.value = !channel.sync_limit;

  if (channel.allowed_extensions) {
    try {
      cfgExtensions.value = JSON.parse(channel.allowed_extensions);
      cfgExtUseGlobal.value = false;
    } catch {
      cfgExtensions.value = [];
      cfgExtUseGlobal.value = true;
    }
  } else {
    cfgExtensions.value = [];
    cfgExtUseGlobal.value = true;
  }
  cfgNewExt.value = "";
  showConfigModal.value = true;
}

function addCfgExt() {
  const ext = cfgNewExt.value.trim().toLowerCase().replace(/^\./, "");
  if (ext && !cfgExtensions.value.includes(ext)) {
    cfgExtensions.value.push(ext);
  }
  cfgNewExt.value = "";
}

function removeCfgExt(ext: string) {
  cfgExtensions.value = cfgExtensions.value.filter(e => e !== ext);
}

async function saveConfig() {
  if (!configChannel.value) return;
  const maxSize = cfgMaxSizeInput.value > 0 ? displayToBytes(cfgMaxSizeInput.value, cfgMaxSizeUnit.value) : 0;
  await channelsStore.updateChannel(configChannel.value.id, {
    filter_type: cfgFilterType.value,
    max_file_size: maxSize,
    allowed_extensions: cfgExtUseGlobal.value ? "" : JSON.stringify(cfgExtensions.value),
    download_path: cfgPathUseGlobal.value ? "" : cfgDownloadPath.value,
    sync_limit: cfgSyncUseGlobal.value ? 0 : cfgSyncLimit.value,
  } as Partial<Channel>);
  showConfigModal.value = false;
}

async function handleSync(channel: Channel) {
  syncing.value = channel.id;
  try {
    const data = await channelsStore.syncChannel(channel.id);
    if (data && data.messages) {
      syncMessages.value = data.messages;
      syncChannelId.value = channel.id;
      syncChannelTitle.value = channel.title;
      selectedMsgIds.value = new Set(
        data.messages.filter((m: SyncMessage) => !m.downloaded).map((m: SyncMessage) => m.message_id)
      );
      showSyncModal.value = true;
    }
  } finally {
    syncing.value = null;
  }
}

function toggleMsgSelect(id: number) {
  if (selectedMsgIds.value.has(id)) {
    selectedMsgIds.value.delete(id);
  } else {
    selectedMsgIds.value.add(id);
  }
  selectedMsgIds.value = new Set(selectedMsgIds.value);
}

function toggleSelectAll() {
  if (selectedMsgIds.value.size === syncMessages.value.length) {
    selectedMsgIds.value = new Set();
  } else {
    selectedMsgIds.value = new Set(syncMessages.value.map(m => m.message_id));
  }
}

const downloadResult = ref("");
const showDuplicateModal = ref(false);
const duplicateMessages = ref<SyncMessage[]>([]);
const pendingNonDuplicateIds = ref<number[]>([]);

async function handleDownloadSelected() {
  if (!syncChannelId.value || selectedMsgIds.value.size === 0) return;

  const selected = syncMessages.value.filter(m => selectedMsgIds.value.has(m.message_id));
  const dupes = selected.filter(m => m.downloaded);
  const fresh = selected.filter(m => !m.downloaded);

  if (dupes.length > 0) {
    duplicateMessages.value = dupes;
    pendingNonDuplicateIds.value = fresh.map(m => m.message_id);
    showDuplicateModal.value = true;
    return;
  }

  await doDownload(selected.map(m => m.message_id), false);
}

async function handleDuplicateChoice(action: "skip" | "force") {
  showDuplicateModal.value = false;
  if (action === "skip") {
    if (pendingNonDuplicateIds.value.length > 0) {
      await doDownload(pendingNonDuplicateIds.value, false);
    } else {
      downloadResult.value = "已跳过所有重复任务，无新任务提交";
    }
  } else {
    const allIds = [
      ...pendingNonDuplicateIds.value,
      ...duplicateMessages.value.map(m => m.message_id),
    ];
    await doDownload(allIds, true);
  }
}

const showResultModal = ref(false);

async function doDownload(msgIds: number[], force: boolean) {
  if (!syncChannelId.value || msgIds.length === 0) return;
  downloading.value = true;
  downloadResult.value = "";
  try {
    const res = await channelsStore.downloadMessages(syncChannelId.value, msgIds, force);
    showSyncModal.value = false;
    downloadResult.value = `已添加 ${res?.submitted ?? 0} 个下载任务` +
      (res?.skipped > 0 ? `，跳过 ${res.skipped} 个` : "");
    showResultModal.value = true;
  } finally {
    downloading.value = false;
  }
}

function formatDate(iso: string): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

const filterTypeOptions = [
  { value: "all", label: "全部类型" },
  { value: "video", label: "仅视频" },
  { value: "photo", label: "仅图片" },
  { value: "document", label: "仅文档" },
  { value: "audio", label: "仅音频" },
];


function openAddModal() {
  showAddModal.value = true;
  addError.value = "";
  const authed = accountsStore.accounts.filter(a => a.authorized);
  if (authed.length > 0 && !selectedAccountId.value) {
    selectedAccountId.value = authed[0].id;
  }
}

const searchFilteredChannels = computed(() => {
  if (!searchAccountId.value) return channelsStore.channels;
  return channelsStore.channels.filter(c => c.account_id === searchAccountId.value);
});

function onSearchAccountChange() {
  searchChannelId.value = null;
}

function openSearchModal() {
  showSearchModal.value = true;
  searchResults.value = [];
  searchCursors.value = {};
  searchHasMore.value = false;
  searchPerformed.value = false;
  expandedSearchIds.value = new Set();
  selectedSearchIds.value = new Set();
  nextTick(setupSearchObserver);
}

function closeSearchModal() {
  showSearchModal.value = false;
  cleanupSearchObserver();
}

function setupSearchObserver() {
  cleanupSearchObserver();
  if (!searchSentinelRef.value) return;
  searchObserver = new IntersectionObserver(
    (entries) => {
      if (entries[0]?.isIntersecting && searchHasMore.value && !searchLoadingMore.value && !searching.value) {
        loadMoreSearch();
      }
    },
    { rootMargin: "100px" }
  );
  searchObserver.observe(searchSentinelRef.value);
}

function cleanupSearchObserver() {
  searchObserver?.disconnect();
  searchObserver = null;
}

function resolveSearchLimit(): number {
  if (searchLimitChoice.value === "custom") {
    return searchCustomLimit.value > 0 ? searchCustomLimit.value : 50;
  }
  const n = Number(searchLimitChoice.value);
  return n > 0 ? n : 50;
}

async function doSearch(append = false) {
  const limit = resolveSearchLimit();
  if (searchLimitChoice.value === "custom" && searchCustomLimit.value <= 0) {
    searchCustomLimit.value = 50;
  }

  if (!append) {
    searching.value = true;
    searchPerformed.value = true;
    searchResults.value = [];
    searchCursors.value = {};
    selectedSearchIds.value = new Set();
  } else {
    searchLoadingMore.value = true;
  }

  try {
    const res = await apiFetch("/api/channels/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        keyword: searchKeyword.value.trim(),
        media_type: searchMediaType.value,
        extensions: searchExtensions.value,
        account_id: searchAccountId.value,
        channel_id: searchChannelId.value,
        per_channel_limit: limit,
        cursors: append ? searchCursors.value : {},
      }),
    });
    if (!res.ok) return;
    const data = await res.json();

    if (append) {
      searchResults.value.push(...data.results);
    } else {
      searchResults.value = data.results;
    }
    searchCursors.value = data.cursors;
    searchHasMore.value = data.has_more;

    nextTick(setupSearchObserver);
  } finally {
    searching.value = false;
    searchLoadingMore.value = false;
  }
}

function loadMoreSearch() {
  if (searchLoadingMore.value || !searchHasMore.value) return;
  doSearch(true);
}

function addSearchExt() {
  const ext = searchNewExt.value.trim().toLowerCase().replace(/^\./, "");
  if (ext && !searchExtensions.value.includes(ext)) {
    searchExtensions.value.push(ext);
  }
  searchNewExt.value = "";
}

function removeSearchExt(ext: string) {
  searchExtensions.value = searchExtensions.value.filter(e => e !== ext);
}

function searchResultKey(r: SearchResult): string {
  return `${r.channel_id}_${r.message_id}`;
}

function toggleSearchDetail(key: string) {
  if (expandedSearchIds.value.has(key)) {
    expandedSearchIds.value.delete(key);
  } else {
    expandedSearchIds.value.add(key);
  }
  expandedSearchIds.value = new Set(expandedSearchIds.value);
}

function toggleSearchSelect(r: SearchResult) {
  const key = searchResultKey(r);
  if (selectedSearchIds.value.has(key)) {
    selectedSearchIds.value.delete(key);
  } else {
    selectedSearchIds.value.add(key);
  }
  selectedSearchIds.value = new Set(selectedSearchIds.value);
}

function toggleSearchSelectAll() {
  if (selectedSearchIds.value.size === searchResults.value.length) {
    selectedSearchIds.value = new Set();
  } else {
    selectedSearchIds.value = new Set(searchResults.value.map(searchResultKey));
  }
}

const searchDuplicateMessages = ref<SearchResult[]>([]);
const showSearchDuplicateModal = ref(false);

async function handleSearchDownload() {
  if (selectedSearchIds.value.size === 0) return;

  const selected = searchResults.value.filter(r => selectedSearchIds.value.has(searchResultKey(r)));
  const dupes = selected.filter(r => r.downloaded);

  if (dupes.length > 0) {
    searchDuplicateMessages.value = dupes;
    showSearchDuplicateModal.value = true;
    return;
  }

  await doSearchDownload(selected, false);
}

async function handleSearchDuplicateChoice(action: "skip" | "force") {
  showSearchDuplicateModal.value = false;
  if (action === "skip") {
    const freshList = searchResults.value.filter(
      r => selectedSearchIds.value.has(searchResultKey(r)) && !r.downloaded
    );
    if (freshList.length > 0) {
      await doSearchDownload(freshList, false);
    } else {
      downloadResult.value = "已跳过所有重复任务，无新任务提交";
      showResultModal.value = true;
    }
  } else {
    const allSelected = searchResults.value.filter(
      r => selectedSearchIds.value.has(searchResultKey(r))
    );
    await doSearchDownload(allSelected, true);
  }
}

async function doSearchDownload(items: SearchResult[], force: boolean) {
  if (items.length === 0) return;
  searchDownloading.value = true;
  downloadResult.value = "";

  const byChannel = new Map<number, number[]>();
  for (const item of items) {
    const arr = byChannel.get(item.channel_id) || [];
    arr.push(item.message_id);
    byChannel.set(item.channel_id, arr);
  }

  let totalSubmitted = 0;
  let totalSkipped = 0;

  try {
    for (const [chId, msgIds] of byChannel) {
      const res = await channelsStore.downloadMessages(chId, msgIds, force);
      totalSubmitted += res?.submitted ?? 0;
      totalSkipped += res?.skipped ?? 0;
    }
    showSearchModal.value = false;
    cleanupSearchObserver();
    downloadResult.value = `已添加 ${totalSubmitted} 个下载任务` +
      (totalSkipped > 0 ? `，跳过 ${totalSkipped} 个` : "");
    showResultModal.value = true;
  } finally {
    searchDownloading.value = false;
  }
}

async function fetchGlobalSettings() {
  const res = await apiFetch("/api/settings");
  if (res.ok) globalSettings.value = await res.json();
}

onMounted(() => {
  channelsStore.fetchChannels();
  accountsStore.fetchAccounts();
  fetchGlobalSettings();
});

onUnmounted(cleanupSearchObserver);
</script>

<template>
  <div class="mx-auto max-w-6xl space-y-4">
    <div class="flex items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <p class="text-sm text-text-secondary">
          已订阅 {{ channelsStore.channels.length }} 个频道
        </p>
        <!-- 按账户筛选 -->
        <select
          v-if="accountsStore.accounts.length > 1"
          v-model.number="filterAccountId"
          class="rounded-lg border border-surface-border bg-surface px-2 py-1 text-xs outline-none focus:border-primary"
        >
          <option :value="null">全部账户</option>
          <option
            v-for="acc in accountsStore.accounts.filter(a => a.authorized)"
            :key="acc.id"
            :value="acc.id"
          >
            {{ acc.first_name || acc.phone }}
          </option>
        </select>
      </div>
      <div class="flex items-center gap-2">
        <button
          class="flex items-center gap-1.5 rounded-lg border border-surface-border px-3 py-1.5 text-sm text-text-secondary cursor-pointer hover:bg-surface hover:text-primary transition-colors"
          @click="openSearchModal"
        >
          <MIcon name="search" :size="16" />
          搜索
        </button>
        <button
          class="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors"
          @click="openAddModal"
        >
          <MIcon name="add" :size="16" />
          添加频道
        </button>
      </div>
    </div>

    <div v-if="filteredChannels.length === 0" class="rounded-xl border border-surface-border bg-surface-2 px-5 py-12 text-center text-sm text-text-muted">
      {{ channelsStore.loading ? "加载中..." : "暂无订阅频道" }}
    </div>

    <div v-else class="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="channel in filteredChannels"
        :key="channel.id"
        class="rounded-xl border border-surface-border bg-surface-2 p-4 transition-colors hover:border-primary/30"
      >
        <div class="flex items-start gap-3">
          <!-- 频道头像 -->
          <div class="shrink-0 h-10 w-10">
            <img
              v-if="!photoErrors.has(channel.id)"
              :src="apiUrl(`/api/channels/${channel.id}/photo`)"
              class="h-10 w-10 rounded-lg object-cover"
              @error="photoErrors.add(channel.id)"
            />
            <div
              v-else
              class="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center"
            >
              <MIcon name="chat" :size="20" class="text-primary" />
            </div>
          </div>

          <div class="flex-1 min-w-0">
            <h3 class="truncate text-sm font-medium">{{ channel.title }}</h3>
            <p v-if="channel.username" class="mt-0.5 text-xs text-text-muted">
              @{{ channel.username }}
            </p>
            <p v-if="channel.account_label" class="mt-0.5 text-xs text-text-muted">
              via {{ channel.account_label }}
            </p>
          </div>

          <button
            class="rounded-md p-1 text-text-muted hover:text-danger cursor-pointer transition-colors shrink-0"
            @click="confirmDeleteId = channel.id"
          >
            <MIcon name="delete" :size="14" />
          </button>
        </div>

        <div class="mt-2 flex flex-wrap items-center gap-2 text-xs text-text-muted">
          <span v-if="channel.filter_type !== 'all'" class="rounded bg-surface px-1.5 py-0.5">
            {{ filterTypeOptions.find(o => o.value === channel.filter_type)?.label }}
          </span>
          <span v-if="channel.max_file_size > 0" class="rounded bg-surface px-1.5 py-0.5">
            &le; {{ statsStore.formatBytes(channel.max_file_size) }}
          </span>
          <span v-if="channel.allowed_extensions" class="rounded bg-surface px-1.5 py-0.5">
            自定义格式
          </span>
        </div>

        <div class="mt-3 flex items-center justify-between">
          <div class="flex items-center gap-2">
            <button
              class="flex items-center gap-1 text-xs text-text-secondary hover:text-primary cursor-pointer transition-colors disabled:opacity-50"
              :disabled="syncing === channel.id"
              @click="handleSync(channel)"
            >
              <MIcon name="sync" :size="14" :class="{ 'animate-spin': syncing === channel.id }" />
              {{ syncing === channel.id ? "同步中..." : "同步" }}
            </button>
            <button
              class="flex items-center gap-1 text-xs text-text-secondary hover:text-primary cursor-pointer transition-colors"
              @click="openConfig(channel)"
            >
              <MIcon name="settings" :size="14" />
              配置
            </button>
          </div>

          <button
            class="flex items-center gap-1 text-xs cursor-pointer transition-colors"
            :class="channel.auto_download ? 'text-primary' : 'text-text-muted'"
            @click="toggleAutoDownload(channel)"
          >
            <MIcon :name="channel.auto_download ? 'toggle_on' : 'toggle_off'" :size="20" :filled="true" />
            自动下载
          </button>
        </div>
      </div>
    </div>

    <!-- Add Channel Modal -->
    <Teleport to="body">
      <div
        v-if="showAddModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="showAddModal = false"
      >
        <div class="w-full max-w-md rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl">
          <h2 class="text-base font-semibold">添加频道</h2>
          <p class="mt-1 text-sm text-text-secondary">
            输入 Telegram 频道或群组的链接或用户名
          </p>

          <div class="mt-4 space-y-3">
            <div>
              <label class="block text-xs text-text-secondary mb-1">使用账户</label>
              <select
                v-model.number="selectedAccountId"
                class="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
              >
                <option
                  v-for="acc in accountsStore.accounts.filter(a => a.authorized)"
                  :key="acc.id"
                  :value="acc.id"
                >
                  {{ acc.first_name || acc.phone }}
                  {{ acc.username ? `(@${acc.username})` : '' }}
                </option>
              </select>
              <p v-if="accountsStore.accounts.filter(a => a.authorized).length === 0" class="mt-1 text-xs text-danger">
                没有已登录的账户，请先在设置中添加
              </p>
            </div>

            <div>
              <label class="block text-xs text-text-secondary mb-1">频道链接</label>
              <input
                v-model="newLink"
                type="text"
                placeholder="https://t.me/channel 或 @channel"
                class="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
                @keyup.enter="handleAdd"
              />
            </div>
          </div>

          <p v-if="addError" class="mt-2 text-xs text-danger">{{ addError }}</p>

          <div class="mt-4 flex justify-end gap-2">
            <button
              class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
              @click="showAddModal = false"
            >
              取消
            </button>
            <button
              class="rounded-lg bg-primary px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
              :disabled="adding || !newLink.trim() || !selectedAccountId"
              @click="handleAdd"
            >
              {{ adding ? "添加中..." : "确认" }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Config Modal -->
    <Teleport to="body">
      <div
        v-if="showConfigModal && configChannel"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="showConfigModal = false"
      >
        <div class="w-full max-w-md rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl max-h-[80vh] overflow-y-auto">
          <h2 class="text-base font-semibold">频道配置</h2>
          <p class="mt-1 text-sm text-text-secondary">{{ configChannel.title }}</p>

          <div class="mt-4 space-y-5">
            <!-- 媒体类型 -->
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">媒体类型</label>
              <select
                v-model="cfgFilterType"
                class="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
              >
                <option v-for="opt in filterTypeOptions" :key="opt.value" :value="opt.value">
                  {{ opt.label }}
                </option>
              </select>
            </div>

            <!-- 最大文件大小 -->
            <div>
              <label class="block text-xs font-medium text-text-secondary mb-1">最大文件大小</label>
              <div class="flex gap-2">
                <input
                  v-model.number="cfgMaxSizeInput"
                  type="number"
                  min="0"
                  placeholder="0 表示不限制"
                  class="flex-1 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
                />
                <select
                  v-model="cfgMaxSizeUnit"
                  class="rounded-lg border border-surface-border bg-surface px-2 py-2 text-sm outline-none focus:border-primary"
                >
                  <option value="MB">MB</option>
                  <option value="GB">GB</option>
                </select>
              </div>
              <p class="mt-1 text-xs text-text-muted">设为 0 表示不限制文件大小</p>
            </div>

            <!-- 媒体格式 -->
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-xs font-medium text-text-secondary">媒体格式</label>
                <div class="flex gap-1">
                  <button
                    class="text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                    :class="cfgExtUseGlobal ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface'"
                    @click="cfgExtUseGlobal = true"
                  >
                    全局
                  </button>
                  <button
                    class="text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                    :class="!cfgExtUseGlobal ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface'"
                    @click="cfgExtUseGlobal = false"
                  >
                    自定义
                  </button>
                </div>
              </div>
              <template v-if="!cfgExtUseGlobal">
                <div class="flex gap-2">
                  <input
                    v-model="cfgNewExt"
                    type="text"
                    placeholder="如 mp4, mkv"
                    class="flex-1 rounded-lg border border-surface-border bg-surface px-2.5 py-1.5 text-xs outline-none focus:border-primary font-mono"
                    @keyup.enter="addCfgExt"
                  />
                  <button
                    class="rounded-lg bg-primary px-2.5 py-1.5 text-xs text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
                    :disabled="!cfgNewExt.trim()"
                    @click="addCfgExt"
                  >
                    添加
                  </button>
                </div>
                <div v-if="cfgExtensions.length > 0" class="mt-2 flex flex-wrap gap-1.5">
                  <span
                    v-for="ext in cfgExtensions"
                    :key="ext"
                    class="inline-flex items-center gap-0.5 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-mono text-primary"
                  >
                    .{{ ext }}
                    <button class="hover:text-danger cursor-pointer" @click="removeCfgExt(ext)">&times;</button>
                  </span>
                </div>
                <p v-else class="mt-1 text-xs text-text-muted">未设置 — 下载所有格式</p>
              </template>
              <div v-else class="mt-1">
                <div v-if="globalSettings.allowed_extensions.length > 0" class="flex flex-wrap gap-1.5">
                  <span
                    v-for="ext in globalSettings.allowed_extensions"
                    :key="ext"
                    class="rounded-full bg-surface px-2 py-0.5 text-xs font-mono text-text-secondary"
                  >.{{ ext }}</span>
                </div>
                <p v-else class="text-xs text-text-muted">全局未设置 — 下载所有格式</p>
              </div>
            </div>

            <!-- 下载目录 -->
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-xs font-medium text-text-secondary">下载目录</label>
                <div class="flex gap-1">
                  <button
                    class="text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                    :class="cfgPathUseGlobal ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface'"
                    @click="cfgPathUseGlobal = true"
                  >
                    全局
                  </button>
                  <button
                    class="text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                    :class="!cfgPathUseGlobal ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface'"
                    @click="cfgPathUseGlobal = false"
                  >
                    自定义
                  </button>
                </div>
              </div>
              <input
                v-if="!cfgPathUseGlobal"
                v-model="cfgDownloadPath"
                type="text"
                placeholder="自定义下载路径"
                class="w-full rounded-lg border border-surface-border bg-surface px-3 py-1.5 text-xs outline-none focus:border-primary font-mono"
              />
              <p v-else class="text-xs text-text-muted font-mono">{{ (globalSettings as Record<string,unknown>).download_path || (globalSettings as Record<string,unknown>).data_dir || '默认路径' }}</p>
            </div>

            <!-- 同步消息数量 -->
            <div>
              <div class="flex items-center justify-between mb-1">
                <label class="text-xs font-medium text-text-secondary">同步消息数量</label>
                <div class="flex gap-1">
                  <button
                    class="text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                    :class="cfgSyncUseGlobal ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface'"
                    @click="cfgSyncUseGlobal = true"
                  >
                    全局
                  </button>
                  <button
                    class="text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                    :class="!cfgSyncUseGlobal ? 'bg-primary/10 text-primary' : 'text-text-muted hover:bg-surface'"
                    @click="cfgSyncUseGlobal = false"
                  >
                    自定义
                  </button>
                </div>
              </div>
              <div v-if="!cfgSyncUseGlobal" class="space-y-1.5">
                <div class="flex items-center gap-2">
                  <input
                    v-model.number="cfgSyncLimit"
                    type="number"
                    min="1"
                    placeholder="输入数量"
                    class="flex-1 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
                  />
                  <span class="text-xs text-text-muted shrink-0">条</span>
                </div>
                <div class="flex flex-wrap gap-1.5">
                  <button
                    v-for="n in [50, 100, 200, 500, 1000]"
                    :key="n"
                    class="text-xs px-2 py-0.5 rounded cursor-pointer transition-colors"
                    :class="cfgSyncLimit === n ? 'bg-primary/10 text-primary' : 'bg-surface text-text-muted hover:text-text-secondary'"
                    @click="cfgSyncLimit = n"
                  >
                    {{ n }}
                  </button>
                </div>
              </div>
              <p v-else class="text-xs text-text-muted">{{ (globalSettings as Record<string,unknown>).sync_limit || 100 }} 条</p>
            </div>
          </div>

          <div class="mt-5 flex justify-end gap-2">
            <button
              class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
              @click="showConfigModal = false"
            >
              取消
            </button>
            <button
              class="rounded-lg bg-primary px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors"
              @click="saveConfig"
            >
              保存
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Sync Preview Modal -->
    <Teleport to="body">
      <div
        v-if="showSyncModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="showSyncModal = false"
      >
        <div class="w-full max-w-2xl rounded-xl border border-surface-border bg-surface-2 shadow-xl flex flex-col max-h-[80vh]">
          <div class="p-5 border-b border-surface-border shrink-0">
            <div class="flex items-center justify-between">
              <div>
                <h2 class="text-base font-semibold">同步结果</h2>
                <p class="mt-0.5 text-xs text-text-muted">{{ syncChannelTitle }} · 共 {{ syncMessages.length }} 条媒体</p>
              </div>
              <div class="flex items-center gap-2">
                <button
                  class="text-xs px-2 py-1 rounded border border-surface-border text-text-secondary hover:bg-surface cursor-pointer transition-colors"
                  @click="toggleSelectAll"
                >
                  {{ selectedMsgIds.size === syncMessages.length ? '取消全选' : '全选' }}
                </button>
                <span class="text-xs text-text-muted">已选 {{ selectedMsgIds.size }}</span>
              </div>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-3">
            <div v-if="syncMessages.length === 0" class="py-10 text-center text-sm text-text-muted">
              没有找到符合过滤条件的媒体
            </div>

            <div v-else class="space-y-1">
              <div
                v-for="msg in syncMessages"
                :key="msg.message_id"
                class="rounded-lg hover:bg-surface transition-colors"
                :class="{ 'bg-primary/5': selectedMsgIds.has(msg.message_id) }"
              >
                <label class="flex items-center gap-3 p-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    :checked="selectedMsgIds.has(msg.message_id)"
                    class="h-4 w-4 rounded accent-primary cursor-pointer"
                    @change="toggleMsgSelect(msg.message_id)"
                  />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm truncate">{{ msg.filename }}</p>
                    <p class="text-xs text-text-muted">
                      {{ msg.media_type }}
                      <span v-if="msg.file_size"> · {{ statsStore.formatBytes(msg.file_size) }}</span>
                      <span v-if="msg.date"> · {{ formatDate(msg.date) }}</span>
                    </p>
                  </div>
                  <span
                    v-if="msg.downloaded"
                    class="shrink-0 text-xs px-1.5 py-0.5 rounded bg-green-500/10 text-green-600"
                  >已下载</span>
                  <button
                    class="shrink-0 rounded-md p-1 text-text-muted hover:text-primary cursor-pointer transition-colors"
                    title="详情"
                    @click.prevent.stop="toggleDetail(msg.message_id)"
                  >
                    <MIcon :name="expandedMsgIds.has(msg.message_id) ? 'expand_less' : 'expand_more'" :size="14" />
                  </button>
                  <span class="text-xs px-1.5 py-0.5 rounded bg-surface text-text-muted shrink-0">
                    {{ msg.media_type }}
                  </span>
                </label>

                <div
                  v-if="expandedMsgIds.has(msg.message_id)"
                  class="mx-11 mb-2.5 rounded-lg bg-surface p-3 text-xs space-y-1.5"
                >
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">文件名</span>
                    <span class="break-all">{{ msg.filename }}</span>
                  </div>
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">大小</span>
                    <span>{{ msg.file_size ? statsStore.formatBytes(msg.file_size) : '未知' }}</span>
                  </div>
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">类型</span>
                    <span>{{ msg.media_type }}</span>
                  </div>
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">消息 ID</span>
                    <span class="font-mono">{{ msg.message_id }}</span>
                  </div>
                  <div v-if="msg.date" class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">时间</span>
                    <span>{{ new Date(msg.date).toLocaleString('zh-CN') }}</span>
                  </div>
                  <div v-if="msg.text" class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">描述</span>
                    <span class="whitespace-pre-wrap break-all">{{ msg.text }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="p-4 border-t border-surface-border shrink-0">
            <div class="flex justify-between items-center">
            <button
              class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
              @click="showSyncModal = false"
            >
              关闭
            </button>
            <button
              class="rounded-lg bg-primary px-4 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
              :disabled="downloading || selectedMsgIds.size === 0"
              @click="handleDownloadSelected"
            >
              {{ downloading ? '提交中...' : `下载选中 (${selectedMsgIds.size})` }}
            </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Duplicate Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="showDuplicateModal"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40"
        @click.self="showDuplicateModal = false"
      >
        <div class="w-full max-w-md rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl">
          <h2 class="text-base font-semibold">发现重复任务</h2>
          <p class="mt-1 text-sm text-text-secondary">
            以下 {{ duplicateMessages.length }} 个文件已有下载记录：
          </p>

          <div class="mt-3 max-h-48 overflow-y-auto space-y-1.5">
            <div
              v-for="msg in duplicateMessages"
              :key="msg.message_id"
              class="flex items-center gap-2 rounded-lg bg-surface px-3 py-2 text-xs"
            >
              <span class="flex-1 truncate">{{ msg.filename }}</span>
              <span v-if="msg.file_size" class="shrink-0 text-text-muted">{{ statsStore.formatBytes(msg.file_size) }}</span>
            </div>
          </div>

          <p v-if="pendingNonDuplicateIds.length > 0" class="mt-2 text-xs text-text-muted">
            另有 {{ pendingNonDuplicateIds.length }} 个新文件将正常下载
          </p>

          <div class="mt-4 flex justify-end gap-2">
            <button
              class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
              @click="showDuplicateModal = false"
            >
              取消
            </button>
            <button
              class="rounded-lg border border-surface-border px-3 py-1.5 text-sm cursor-pointer hover:bg-surface transition-colors"
              @click="handleDuplicateChoice('skip')"
            >
              跳过已存在
            </button>
            <button
              class="rounded-lg bg-warning px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-warning/80 transition-colors"
              @click="handleDuplicateChoice('force')"
            >
              全部强制下载
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Download Result Modal -->
    <Teleport to="body">
      <div
        v-if="showResultModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="showResultModal = false"
      >
        <div class="w-full max-w-xs rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl text-center">
          <h2 class="text-base font-semibold">下载任务</h2>
          <p class="mt-3 text-sm text-text-secondary">{{ downloadResult }}</p>
          <div class="mt-4">
            <button
              class="rounded-lg bg-primary px-4 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors"
              @click="showResultModal = false"
            >
              确定
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Confirm Delete Modal -->
    <Teleport to="body">
      <div
        v-if="confirmDeleteId !== null"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="confirmDeleteId = null"
      >
        <div class="w-full max-w-xs rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl">
          <h2 class="text-base font-semibold">确认删除</h2>
          <p class="mt-2 text-sm text-text-secondary">
            删除后该频道的订阅和过滤规则将被清除，确定要删除吗？
          </p>
          <div class="mt-4 flex justify-end gap-2">
            <button
              class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
              @click="confirmDeleteId = null"
            >
              取消
            </button>
            <button
              class="rounded-lg bg-danger px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-danger/80 transition-colors"
              @click="channelsStore.deleteChannel(confirmDeleteId!); confirmDeleteId = null"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Search Modal -->
    <Teleport to="body">
      <div
        v-if="showSearchModal"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="closeSearchModal"
      >
        <div class="w-full max-w-3xl rounded-xl border border-surface-border bg-surface-2 shadow-xl flex flex-col max-h-[85vh]">
          <!-- 搜索头部 -->
          <div class="p-5 border-b border-surface-border shrink-0 space-y-3">
            <div class="flex items-center justify-between">
              <h2 class="text-base font-semibold">搜索媒体</h2>
              <button
                class="rounded-md p-1 text-text-muted hover:text-text-primary cursor-pointer transition-colors"
                @click="closeSearchModal"
              >
                <MIcon name="close" :size="18" />
              </button>
            </div>

            <!-- 搜索输入 -->
            <div class="flex gap-2">
              <input
                v-model="searchKeyword"
                type="text"
                placeholder="输入关键字搜索文件名..."
                class="flex-1 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
                @keyup.enter="doSearch()"
              />
              <div class="flex items-center gap-1 shrink-0">
                <select
                  v-model="searchLimitChoice"
                  class="rounded-lg border border-surface-border bg-surface px-2 py-2 text-sm outline-none focus:border-primary"
                  title="每频道扫描消息数"
                >
                  <option v-for="n in [10, 50, 100, 200, 500, 1000]" :key="n" :value="String(n)">{{ n }} 条</option>
                  <option value="custom">自定义</option>
                </select>
                <input
                  v-if="searchLimitChoice === 'custom'"
                  v-model.number="searchCustomLimit"
                  type="number"
                  min="1"
                  placeholder="条数"
                  class="w-16 rounded-lg border border-surface-border bg-surface px-2 py-2 text-sm outline-none focus:border-primary"
                />
              </div>
              <button
                class="rounded-lg bg-primary px-4 py-2 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
                :disabled="searching"
                @click="doSearch()"
              >
                <MIcon v-if="searching" name="sync" :size="16" class="animate-spin" />
                <template v-else>搜索</template>
              </button>
            </div>

            <!-- 过滤器 -->
            <div class="flex flex-wrap items-end gap-3">
              <div>
                <label class="block text-xs text-text-muted mb-1">账户</label>
                <select
                  v-model.number="searchAccountId"
                  class="rounded-lg border border-surface-border bg-surface px-2.5 py-1.5 text-xs outline-none focus:border-primary"
                  @change="onSearchAccountChange"
                >
                  <option :value="null">全部账户</option>
                  <option
                    v-for="acc in accountsStore.accounts.filter(a => a.authorized)"
                    :key="acc.id"
                    :value="acc.id"
                  >
                    {{ acc.first_name || acc.phone }}
                  </option>
                </select>
              </div>

              <div>
                <label class="block text-xs text-text-muted mb-1">频道</label>
                <select
                  v-model.number="searchChannelId"
                  class="rounded-lg border border-surface-border bg-surface px-2.5 py-1.5 text-xs outline-none focus:border-primary max-w-[200px]"
                >
                  <option :value="null">全部频道</option>
                  <option
                    v-for="ch in searchFilteredChannels"
                    :key="ch.id"
                    :value="ch.id"
                  >
                    {{ ch.title }}
                  </option>
                </select>
              </div>

              <div>
                <label class="block text-xs text-text-muted mb-1">媒体类型</label>
                <select
                  v-model="searchMediaType"
                  class="rounded-lg border border-surface-border bg-surface px-2.5 py-1.5 text-xs outline-none focus:border-primary"
                >
                  <option v-for="opt in filterTypeOptions" :key="opt.value" :value="opt.value">
                    {{ opt.label }}
                  </option>
                </select>
              </div>

              <div class="flex-1 min-w-[180px]">
                <label class="block text-xs text-text-muted mb-1">媒体后缀</label>
                <div class="flex gap-1.5">
                  <input
                    v-model="searchNewExt"
                    type="text"
                    placeholder="如 mp4, mkv"
                    class="flex-1 rounded-lg border border-surface-border bg-surface px-2.5 py-1.5 text-xs outline-none focus:border-primary font-mono"
                    @keyup.enter="addSearchExt"
                  />
                  <button
                    class="rounded-lg bg-primary/10 px-2 py-1.5 text-xs text-primary cursor-pointer hover:bg-primary/20 transition-colors disabled:opacity-50"
                    :disabled="!searchNewExt.trim()"
                    @click="addSearchExt"
                  >
                    添加
                  </button>
                </div>
              </div>
            </div>

            <!-- 已添加的后缀标签 -->
            <div v-if="searchExtensions.length > 0" class="flex flex-wrap gap-1.5">
              <span
                v-for="ext in searchExtensions"
                :key="ext"
                class="inline-flex items-center gap-0.5 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-mono text-primary"
              >
                .{{ ext }}
                <button class="hover:text-danger cursor-pointer" @click="removeSearchExt(ext)">&times;</button>
              </span>
            </div>
          </div>

          <!-- 搜索结果 -->
          <div class="flex-1 overflow-y-auto p-3 min-h-0">
            <!-- 未搜索时的提示 / 无结果 -->
            <div v-if="searchResults.length === 0 && !searching" class="py-16 text-center text-sm text-text-muted">
              <template v-if="searchPerformed">
                <MIcon name="search_off" :size="32" class="text-text-muted/50 mx-auto mb-2" />
                <p>未找到匹配的媒体文件</p>
              </template>
              <template v-else>
                输入关键字或设置过滤条件后点击搜索
              </template>
            </div>

            <!-- 搜索中 -->
            <div v-if="searching && searchResults.length === 0" class="py-16 text-center">
              <MIcon name="sync" :size="24" class="animate-spin text-primary" />
              <p class="mt-2 text-sm text-text-muted">正在搜索所有订阅频道...</p>
            </div>

            <!-- 结果列表 -->
            <div v-if="searchResults.length > 0" class="space-y-1">
              <div
                v-for="r in searchResults"
                :key="searchResultKey(r)"
                class="rounded-lg hover:bg-surface transition-colors"
                :class="{ 'bg-primary/5': selectedSearchIds.has(searchResultKey(r)) }"
              >
                <label class="flex items-center gap-3 p-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    :checked="selectedSearchIds.has(searchResultKey(r))"
                    class="h-4 w-4 rounded accent-primary cursor-pointer shrink-0"
                    @change="toggleSearchSelect(r)"
                  />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm truncate">{{ r.filename }}</p>
                    <p class="text-xs text-text-muted">
                      <span class="text-primary/80">{{ r.channel_title }}</span>
                      <span> · {{ r.media_type }}</span>
                      <span v-if="r.file_size"> · {{ statsStore.formatBytes(r.file_size) }}</span>
                      <span v-if="r.date"> · {{ formatDate(r.date) }}</span>
                    </p>
                  </div>
                  <span
                    v-if="r.downloaded"
                    class="shrink-0 text-xs px-1.5 py-0.5 rounded bg-green-500/10 text-green-600"
                  >已下载</span>
                  <button
                    class="shrink-0 rounded-md p-1 text-text-muted hover:text-primary cursor-pointer transition-colors"
                    title="详情"
                    @click.prevent.stop="toggleSearchDetail(searchResultKey(r))"
                  >
                    <MIcon :name="expandedSearchIds.has(searchResultKey(r)) ? 'expand_less' : 'expand_more'" :size="14" />
                  </button>
                  <span class="text-xs px-1.5 py-0.5 rounded bg-surface text-text-muted shrink-0">
                    {{ r.media_type }}
                  </span>
                </label>

                <div
                  v-if="expandedSearchIds.has(searchResultKey(r))"
                  class="mx-11 mb-2.5 rounded-lg bg-surface p-3 text-xs space-y-1.5"
                >
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">频道</span>
                    <span class="break-all">{{ r.channel_title }}</span>
                  </div>
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">文件名</span>
                    <span class="break-all">{{ r.filename }}</span>
                  </div>
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">大小</span>
                    <span>{{ r.file_size ? statsStore.formatBytes(r.file_size) : '未知' }}</span>
                  </div>
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">类型</span>
                    <span>{{ r.media_type }}</span>
                  </div>
                  <div class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">消息 ID</span>
                    <span class="font-mono">{{ r.message_id }}</span>
                  </div>
                  <div v-if="r.date" class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">时间</span>
                    <span>{{ new Date(r.date).toLocaleString('zh-CN') }}</span>
                  </div>
                  <div v-if="r.text" class="flex gap-4">
                    <span class="text-text-muted shrink-0 w-16">描述</span>
                    <span class="whitespace-pre-wrap break-all">{{ r.text }}</span>
                  </div>
                </div>
              </div>

              <!-- 懒加载哨兵 -->
              <div ref="searchSentinelRef" class="py-3 text-center">
                <template v-if="searchLoadingMore">
                  <MIcon name="sync" :size="18" class="animate-spin text-primary" />
                  <span class="ml-1.5 text-xs text-text-muted">加载更多...</span>
                </template>
                <span v-else-if="!searchHasMore && searchResults.length > 0" class="text-xs text-text-muted">
                  已加载全部结果
                </span>
              </div>
            </div>
          </div>

          <!-- 底部操作栏 -->
          <div v-if="searchResults.length > 0" class="p-4 border-t border-surface-border shrink-0">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <button
                  class="text-xs px-2 py-1 rounded border border-surface-border text-text-secondary hover:bg-surface cursor-pointer transition-colors"
                  @click="toggleSearchSelectAll"
                >
                  {{ selectedSearchIds.size === searchResults.length ? '取消全选' : '全选' }}
                </button>
                <span class="text-xs text-text-muted">
                  共 {{ searchResults.length }} 条 · 已选 {{ selectedSearchIds.size }}
                </span>
              </div>
              <button
                class="rounded-lg bg-primary px-4 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
                :disabled="searchDownloading || selectedSearchIds.size === 0"
                @click="handleSearchDownload"
              >
                {{ searchDownloading ? '提交中...' : `下载选中 (${selectedSearchIds.size})` }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Search Duplicate Confirmation Modal -->
    <Teleport to="body">
      <div
        v-if="showSearchDuplicateModal"
        class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40"
        @click.self="showSearchDuplicateModal = false"
      >
        <div class="w-full max-w-md rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl">
          <h2 class="text-base font-semibold">发现重复任务</h2>
          <p class="mt-1 text-sm text-text-secondary">
            以下 {{ searchDuplicateMessages.length }} 个文件已有下载记录：
          </p>

          <div class="mt-3 max-h-48 overflow-y-auto space-y-1.5">
            <div
              v-for="msg in searchDuplicateMessages"
              :key="searchResultKey(msg)"
              class="flex items-center gap-2 rounded-lg bg-surface px-3 py-2 text-xs"
            >
              <span class="flex-1 truncate">{{ msg.filename }}</span>
              <span class="shrink-0 text-text-muted">{{ msg.channel_title }}</span>
            </div>
          </div>

          <div class="mt-4 flex justify-end gap-2">
            <button
              class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
              @click="showSearchDuplicateModal = false"
            >
              取消
            </button>
            <button
              class="rounded-lg border border-surface-border px-3 py-1.5 text-sm cursor-pointer hover:bg-surface transition-colors"
              @click="handleSearchDuplicateChoice('skip')"
            >
              跳过已存在
            </button>
            <button
              class="rounded-lg bg-warning px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-warning/80 transition-colors"
              @click="handleSearchDuplicateChoice('force')"
            >
              全部强制下载
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
