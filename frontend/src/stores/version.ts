import { defineStore } from "pinia";
import { onMounted, ref } from "vue";
import { APP_VERSION } from "@/constants/app";
import { apiFetch } from "@/utils/api";
import { readApiError } from "@/utils/apiError";

export interface ChangelogItem {
  type: string;
  text: string;
}

export interface ChangelogEntry {
  version: string;
  date: string;
  title?: string;
  items: ChangelogItem[];
}

function normalizeItem(item: ChangelogItem | string): ChangelogItem {
  if (typeof item === "string") return { type: "其他", text: item };
  return item;
}

export const useVersionStore = defineStore("version", () => {
  const hasUpdate = ref(false);
  const latest = ref("");
  const current = ref(APP_VERSION);
  const remoteUrl = ref("https://github.com/iStarCc/TGMedia");
  const checkError = ref("");
  const changelog = ref<ChangelogEntry[]>([]);
  const loading = ref(false);

  async function loadVersionInfo() {
    loading.value = true;
    try {
      const res = await apiFetch("/api/version");
      if (res.ok) {
        const data = await res.json();
        current.value = data.version ?? APP_VERSION;
        changelog.value = (data.changelog ?? []).map((entry: ChangelogEntry) => ({
          ...entry,
          items: (entry.items ?? []).map(normalizeItem),
        }));
        if (data.repository) {
          remoteUrl.value = `https://github.com/${data.repository}`;
        }
      }
    } finally {
      loading.value = false;
    }
  }

  async function checkUpdate(): Promise<Error | null> {
    try {
      const res = await apiFetch("/api/version/check");
      if (res.ok) {
        const data = await res.json();
        hasUpdate.value = !!data.has_update;
        latest.value = data.latest ?? current.value;
        current.value = data.current ?? current.value;
        if (data.remote_url) remoteUrl.value = data.remote_url;
        checkError.value = data.check_error || "";
        return null;
      }
      const err = await readApiError(res);
      checkError.value = err.message;
      return err;
    } catch {
      checkError.value = "无法检查更新";
      return new Error(checkError.value);
    }
  }

  async function refresh() {
    checkError.value = "";
    await loadVersionInfo();
    await checkUpdate();
  }

  async function refreshWithDialog(showError: (err: unknown, fallback?: string) => void) {
    checkError.value = "";
    await loadVersionInfo();
    const err = await checkUpdate();
    if (err) showError(err, "检查更新失败");
  }

  onMounted(refresh);

  return {
    hasUpdate,
    latest,
    current,
    remoteUrl,
    checkError,
    changelog,
    loading,
    loadVersionInfo,
    checkUpdate,
    refresh,
    refreshWithDialog,
  };
});
