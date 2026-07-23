import { defineStore } from "pinia";
import { ref } from "vue";
import { apiFetch } from "@/utils/api";

export interface Channel {
  id: number;
  account_id: number | null;
  telegram_id: number;
  title: string;
  username: string | null;
  photo_url: string | null;
  auto_download: boolean;
  filter_type: string;
  max_file_size: number;
  allowed_extensions: string;
  download_path: string;
  sync_limit: number;
  created_at: string;
  updated_at: string;
  account_label?: string;
  account_username?: string;
}

export const useChannelsStore = defineStore("channels", () => {
  const channels = ref<Channel[]>([]);
  const loading = ref(false);

  async function fetchChannels() {
    loading.value = true;
    try {
      const res = await apiFetch("/api/channels");
      if (res.ok) channels.value = await res.json();
    } finally {
      loading.value = false;
    }
  }

  async function addChannel(link: string, accountId: number) {
    const res = await apiFetch("/api/channels", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ link, account_id: accountId }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "添加失败");
    }
    const channel = await res.json();
    channels.value.unshift(channel);
    return channel;
  }

  async function deleteChannel(id: number) {
    await apiFetch(`/api/channels/${id}`, { method: "DELETE" });
    channels.value = channels.value.filter((c) => c.id !== id);
  }

  async function syncChannel(id: number) {
    const res = await apiFetch(`/api/channels/${id}/sync`, { method: "POST" });
    if (res.ok) return await res.json();
  }

  async function downloadMessages(channelId: number, messageIds: number[], force = false) {
    const res = await apiFetch(`/api/channels/${channelId}/download`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message_ids: messageIds, force }),
    });
    if (res.ok) return await res.json();
  }

  async function updateChannel(id: number, data: Partial<Channel>) {
    await apiFetch(`/api/channels/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const ch = channels.value.find((c) => c.id === id);
    if (ch) Object.assign(ch, data);
  }

  return { channels, loading, fetchChannels, addChannel, deleteChannel, syncChannel, downloadMessages, updateChannel };
});
