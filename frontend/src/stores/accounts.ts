import { defineStore } from "pinia";
import { ref } from "vue";
import { apiFetch } from "@/utils/api";
import { readApiError } from "@/utils/apiError";

export interface Account {
  id: number;
  phone: string;
  telegram_id: number | null;
  first_name: string;
  last_name: string;
  username: string;
  is_active: number;
  authorized: boolean;
  created_at: string;
}

export const useAccountsStore = defineStore("accounts", () => {
  const accounts = ref<Account[]>([]);
  const loading = ref(false);

  async function fetchAccounts() {
    loading.value = true;
    try {
      const res = await apiFetch("/api/auth/accounts");
      if (res.ok) accounts.value = await res.json();
    } finally {
      loading.value = false;
    }
  }

  async function createAccount(
    phone: string, apiId: number, apiHash: string,
  ): Promise<{ id: number; phone: string }> {
    const res = await apiFetch("/api/auth/accounts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ phone, api_id: apiId, api_hash: apiHash }),
    });
    if (!res.ok) throw await readApiError(res);
    const data = await res.json();
    await fetchAccounts();
    return data;
  }

  async function deleteAccount(id: number) {
    const res = await apiFetch(`/api/auth/accounts/${id}`, { method: "DELETE" });
    if (!res.ok) throw await readApiError(res);
    accounts.value = accounts.value.filter((a) => a.id !== id);
  }

  async function sendCode(accountId: number, phone: string) {
    const res = await apiFetch("/api/auth/send-code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id: accountId, phone }),
    });
    if (!res.ok) throw await readApiError(res);
    return (await res.json()).phone_code_hash as string;
  }

  async function verify(
    accountId: number,
    phone: string,
    code: string,
    phoneCodeHash: string,
  ): Promise<{ needs2FA: boolean; user?: Record<string, unknown> }> {
    const res = await apiFetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        account_id: accountId,
        phone,
        code,
        phone_code_hash: phoneCodeHash,
      }),
    });
    if (res.status === 403) return { needs2FA: true };
    if (!res.ok) throw await readApiError(res);
    await fetchAccounts();
    return { needs2FA: false, user: await res.json() };
  }

  async function verify2FA(accountId: number, password: string) {
    const res = await apiFetch("/api/auth/verify-2fa", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ account_id: accountId, password }),
    });
    if (!res.ok) throw await readApiError(res);
    await fetchAccounts();
    return await res.json();
  }

  return {
    accounts,
    loading,
    fetchAccounts,
    createAccount,
    deleteAccount,
    sendCode,
    verify,
    verify2FA,
  };
});
