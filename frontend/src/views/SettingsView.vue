<script setup lang="ts">
import { onMounted, ref } from "vue";
import { storeToRefs } from "pinia";
import MIcon from "@/components/common/MIcon.vue";
import { useAccountsStore, type Account } from "@/stores/accounts";
import { apiFetch, apiUrl } from "@/utils/api";
import CountryCodeSelect from "@/components/common/CountryCodeSelect.vue";
import AboutPanel from "@/components/settings/AboutPanel.vue";
import { useVersionStore } from "@/stores/version";

interface AppSettings {
  max_concurrent: number;
  auto_download: boolean;
  ws_throttle_ms: number;
  data_dir: string;
  download_path: string;
  download_by_channel: boolean;
  download_by_media_type: boolean;
  allowed_extensions: string[];
  sync_limit: number;
  sync_days: number;
}

const tabs = ["账户", "下载", "关于"] as const;
type Tab = typeof tabs[number];
const activeTab = ref<Tab>("账户");

const accountsStore = useAccountsStore();
const versionStore = useVersionStore();
const { hasUpdate } = storeToRefs(versionStore);

const appSettings = ref<AppSettings>({
  max_concurrent: 3,
  auto_download: false,
  ws_throttle_ms: 500,
  data_dir: "",
  download_path: "",
  download_by_channel: false,
  download_by_media_type: false,
  allowed_extensions: [],
  sync_limit: 100,
  sync_days: 0,
});
const saving = ref(false);
const newExtension = ref("");

const showAddAccount = ref(false);
const countryCode = ref("+86");
const newPhone = ref("");
const newApiId = ref("");
const newApiHash = ref("");
const loginAccountId = ref<number | null>(null);
const loginStep = ref<"idle" | "code" | "2fa">("idle");
const code = ref("");
const password2fa = ref("");
const phoneCodeHash = ref("");
const loginError = ref("");
const addingAccount = ref(false);
const checkingStatus = ref(false);
const confirmDeleteId = ref<number | null>(null);
const avatarErrors = ref<Set<number>>(new Set());

async function checkAllStatus() {
  checkingStatus.value = true;
  try {
    await accountsStore.fetchAccounts();
    avatarErrors.value = new Set();
  } finally {
    checkingStatus.value = false;
  }
}

async function fetchSettings() {
  const res = await apiFetch("/api/settings");
  if (res.ok) appSettings.value = await res.json();
}

async function saveSettings() {
  saving.value = true;
  try {
    await apiFetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        max_concurrent: appSettings.value.max_concurrent,
        auto_download: appSettings.value.auto_download,
        download_path: appSettings.value.download_path,
        download_by_channel: appSettings.value.download_by_channel,
        download_by_media_type: appSettings.value.download_by_media_type,
        allowed_extensions: appSettings.value.allowed_extensions,
        sync_limit: appSettings.value.sync_limit,
        sync_days: appSettings.value.sync_days,
      }),
    });
  } finally {
    saving.value = false;
  }
}

function addExtension() {
  const ext = newExtension.value.trim().toLowerCase().replace(/^\./, "");
  if (ext && !appSettings.value.allowed_extensions.includes(ext)) {
    appSettings.value.allowed_extensions.push(ext);
  }
  newExtension.value = "";
}

function removeExtension(ext: string) {
  appSettings.value.allowed_extensions = appSettings.value.allowed_extensions.filter(e => e !== ext);
}

async function handleAddAccount() {
  if (!newPhone.value.trim() || !newApiId.value.trim() || !newApiHash.value.trim()) return;
  addingAccount.value = true;
  loginError.value = "";
  const fullPhone = countryCode.value + newPhone.value.trim();
  let accId: number | null = null;
  try {
    const acc = await accountsStore.createAccount(
      fullPhone,
      Number(newApiId.value),
      newApiHash.value.trim(),
    );
    accId = acc.id;
    loginAccountId.value = acc.id;

    const hash = await accountsStore.sendCode(acc.id, fullPhone);
    phoneCodeHash.value = hash;
    loginStep.value = "code";
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : "操作失败";
    loginError.value = msg.includes("invalid")
      ? "API ID 或 API Hash 无效，请检查后重新填写"
      : msg;
    if (accId) {
      await accountsStore.deleteAccount(accId);
      loginAccountId.value = null;
    }
  } finally {
    addingAccount.value = false;
  }
}

async function handleVerifyCode() {
  if (!loginAccountId.value) return;
  loginError.value = "";
  const phone = accountsStore.accounts.find(a => a.id === loginAccountId.value)?.phone || newPhone.value;
  try {
    const result = await accountsStore.verify(
      loginAccountId.value, phone, code.value, phoneCodeHash.value
    );
    if (result.needs2FA) {
      loginStep.value = "2fa";
    } else {
      resetLoginState();
    }
  } catch (e: unknown) {
    loginError.value = e instanceof Error ? e.message : "验证失败";
  }
}

async function handleVerify2FA() {
  if (!loginAccountId.value) return;
  loginError.value = "";
  try {
    await accountsStore.verify2FA(loginAccountId.value, password2fa.value);
    resetLoginState();
  } catch (e: unknown) {
    loginError.value = e instanceof Error ? e.message : "验证失败";
  }
}

function resetLoginState() {
  if (loginAccountId.value) {
    avatarErrors.value.delete(loginAccountId.value);
  }
  loginAccountId.value = null;
  loginStep.value = "idle";
  code.value = "";
  password2fa.value = "";
  phoneCodeHash.value = "";
  loginError.value = "";
  countryCode.value = "+86";
  newPhone.value = "";
  newApiId.value = "";
  newApiHash.value = "";
  showAddAccount.value = false;
}

async function startLogin(account: Account) {
  loginAccountId.value = account.id;
  newPhone.value = account.phone;
  loginError.value = "";
  showAddAccount.value = true;
  try {
    const hash = await accountsStore.sendCode(account.id, account.phone);
    phoneCodeHash.value = hash;
    loginStep.value = "code";
  } catch (e: unknown) {
    loginError.value = e instanceof Error ? e.message : "发送验证码失败";
  }
}

function displayName(account: Account): string {
  if (account.first_name) {
    return `${account.first_name} ${account.last_name}`.trim();
  }
  return account.phone;
}

onMounted(() => {
  fetchSettings();
  accountsStore.fetchAccounts();
});
</script>

<template>
  <div class="mx-auto" :class="activeTab === '关于' ? 'max-w-3xl' : 'max-w-2xl'">
    <!-- Tab Bar -->
    <div class="flex gap-1 border-b border-surface-border mb-6">
      <button
        v-for="tab in tabs"
        :key="tab"
        class="px-4 py-2 text-sm transition-colors cursor-pointer -mb-px"
        :class="activeTab === tab
          ? 'text-primary border-b-2 border-primary font-medium'
          : 'text-text-muted hover:text-text-secondary'"
        @click="activeTab = tab"
      >
        <span class="relative inline-flex items-center gap-1.5">
          {{ tab }}
          <span
            v-if="tab === '关于' && hasUpdate"
            class="h-1.5 w-1.5 rounded-full bg-danger"
          />
        </span>
      </button>
    </div>

    <!-- Tab: 账户 -->
    <div v-show="activeTab === '账户'" class="space-y-6">
      <section class="rounded-xl border border-surface-border bg-surface-2 p-5">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-semibold">Telegram 账户</h3>
          <div class="flex items-center gap-2">
            <button
              class="flex items-center gap-1.5 rounded-lg border border-surface-border px-3 py-1.5 text-xs text-text-secondary cursor-pointer hover:bg-surface transition-colors disabled:opacity-50"
              :disabled="checkingStatus || accountsStore.accounts.length === 0"
              title="检查所有账户登录状态"
              @click="checkAllStatus"
            >
              <MIcon name="sync" :size="14" :class="{ 'animate-spin': checkingStatus }" />
              检查状态
            </button>
            <button
              class="flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs text-white cursor-pointer hover:bg-primary-hover transition-colors"
              @click="showAddAccount = true"
            >
              <MIcon name="add" :size="14" />
              添加账户
            </button>
          </div>
        </div>

        <div v-if="accountsStore.accounts.length === 0" class="mt-4 text-sm text-text-muted text-center py-6">
          暂无账户，点击上方按钮添加
        </div>

        <div v-else class="mt-3 space-y-2">
          <div
            v-for="account in accountsStore.accounts"
            :key="account.id"
            class="flex items-center gap-3 rounded-lg border border-surface-border p-3"
          >
            <div class="relative shrink-0 h-9 w-9">
              <img
                v-if="!avatarErrors.has(account.id)"
                :src="apiUrl(`/api/auth/accounts/${account.id}/avatar`)"
                class="h-9 w-9 rounded-full object-cover"
                @error="avatarErrors.add(account.id)"
              />
              <MIcon
                v-else
                name="account_circle"
                :size="36"
                class="text-text-muted"
              />
              <span
                class="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full border-2 border-surface-2"
                :class="account.authorized ? 'bg-green-500' : 'bg-red-400'"
              />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium truncate">{{ displayName(account) }}</p>
              <p class="text-xs text-text-muted">
                {{ account.phone }}
                <span v-if="account.username" class="ml-1">@{{ account.username }}</span>
              </p>
            </div>
            <span
              class="text-xs px-2 py-0.5 rounded-full"
              :class="account.authorized
                ? 'bg-green-500/10 text-green-500'
                : 'bg-danger/10 text-danger'"
            >
              {{ account.authorized ? "已登录" : "未登录" }}
            </span>
            <button
              v-if="!account.authorized"
              class="rounded-md p-1.5 text-text-muted hover:text-primary cursor-pointer transition-colors"
              title="登录"
              @click="startLogin(account)"
            >
              <MIcon name="login" :size="16" />
            </button>
            <button
              class="rounded-md p-1.5 text-text-muted hover:text-danger cursor-pointer transition-colors"
              title="删除"
              @click="confirmDeleteId = account.id"
            >
              <MIcon name="delete" :size="16" />
            </button>
          </div>
        </div>

        <p v-if="loginError && !showAddAccount" class="mt-2 text-xs text-danger">{{ loginError }}</p>
      </section>
    </div>

    <!-- Tab: 下载 -->
    <div v-show="activeTab === '下载'" class="space-y-6">
      <!-- 存储路径 -->
      <section class="rounded-xl border border-surface-border bg-surface-2 p-5">
        <h3 class="text-sm font-semibold">存储路径</h3>
        <div class="mt-3">
          <label class="block text-xs text-text-secondary mb-1">下载保存目录</label>
          <input
            v-model="appSettings.download_path"
            type="text"
            :placeholder="appSettings.data_dir"
            class="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary font-mono"
          />
          <p class="mt-1 text-xs text-text-muted">留空则使用默认路径: {{ appSettings.data_dir }}</p>
          <div class="mt-4 flex items-center justify-between rounded-lg border border-surface-border bg-surface px-3 py-2.5">
            <div>
              <p class="text-sm">按订阅频道创建目录</p>
              <p class="mt-0.5 text-xs text-text-muted">开启后在保存目录下按频道名称分子文件夹</p>
            </div>
            <button
              class="relative h-5 w-9 shrink-0 rounded-full transition-colors cursor-pointer"
              :class="appSettings.download_by_channel ? 'bg-primary' : 'bg-surface-border'"
              @click="appSettings.download_by_channel = !appSettings.download_by_channel"
            >
              <span
                class="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform"
                :class="appSettings.download_by_channel ? 'translate-x-4' : ''"
              />
            </button>
          </div>
          <div class="mt-3 flex items-center justify-between rounded-lg border border-surface-border bg-surface px-3 py-2.5">
            <div>
              <p class="text-sm">按媒体类型创建目录</p>
              <p class="mt-0.5 text-xs text-text-muted">开启后在保存目录下按 photo / video / audio / document 分子文件夹</p>
            </div>
            <button
              class="relative h-5 w-9 shrink-0 rounded-full transition-colors cursor-pointer"
              :class="appSettings.download_by_media_type ? 'bg-primary' : 'bg-surface-border'"
              @click="appSettings.download_by_media_type = !appSettings.download_by_media_type"
            >
              <span
                class="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform"
                :class="appSettings.download_by_media_type ? 'translate-x-4' : ''"
              />
            </button>
          </div>
        </div>
      </section>

      <!-- 下载控制 -->
      <section class="rounded-xl border border-surface-border bg-surface-2 p-5">
        <h3 class="text-sm font-semibold">下载控制</h3>
        <div class="mt-4 space-y-4">
          <div>
            <label class="block text-xs text-text-secondary mb-1">最大并发下载数</label>
            <select
              v-model.number="appSettings.max_concurrent"
              class="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
            >
              <option :value="1">1</option>
              <option :value="3">3</option>
              <option :value="5">5</option>
              <option :value="10">10</option>
            </select>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-sm">自动下载新媒体</span>
            <button
              class="relative h-5 w-9 rounded-full transition-colors cursor-pointer"
              :class="appSettings.auto_download ? 'bg-primary' : 'bg-surface-border'"
              @click="appSettings.auto_download = !appSettings.auto_download"
            >
              <span
                class="absolute top-0.5 left-0.5 h-4 w-4 rounded-full bg-white shadow transition-transform"
                :class="appSettings.auto_download ? 'translate-x-4' : ''"
              />
            </button>
          </div>
        </div>
      </section>

      <!-- 格式过滤 -->
      <section class="rounded-xl border border-surface-border bg-surface-2 p-5">
        <h3 class="text-sm font-semibold">媒体格式过滤</h3>
        <p class="mt-1 text-xs text-text-muted">
          仅下载指定后缀的文件，留空表示不过滤（下载所有格式）
        </p>

        <div class="mt-3 flex gap-2">
          <input
            v-model="newExtension"
            type="text"
            placeholder="例如 mp4, mkv, jpg"
            class="flex-1 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary font-mono"
            @keyup.enter="addExtension"
          />
          <button
            class="rounded-lg bg-primary px-3 py-2 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
            :disabled="!newExtension.trim()"
            @click="addExtension"
          >
            添加
          </button>
        </div>

        <div v-if="appSettings.allowed_extensions.length > 0" class="mt-3 flex flex-wrap gap-2">
          <span
            v-for="ext in appSettings.allowed_extensions"
            :key="ext"
            class="inline-flex items-center gap-1 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-mono text-primary"
          >
            .{{ ext }}
            <button
              class="hover:text-danger cursor-pointer transition-colors"
              @click="removeExtension(ext)"
            >
              &times;
            </button>
          </span>
        </div>
        <p v-else class="mt-3 text-xs text-text-muted">未设置过滤 — 下载所有格式</p>
      </section>

      <!-- 历史同步 -->
      <section class="rounded-xl border border-surface-border bg-surface-2 p-5">
        <h3 class="text-sm font-semibold">历史同步</h3>
        <p class="mt-1 text-xs text-text-muted">同步频道历史消息时的默认参数</p>

        <div class="mt-4 space-y-4">
          <div>
            <label class="block text-xs text-text-secondary mb-1">最大消息数量</label>
            <select
              v-model.number="appSettings.sync_limit"
              class="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
            >
              <option :value="50">50 条</option>
              <option :value="100">100 条</option>
              <option :value="200">200 条</option>
              <option :value="500">500 条</option>
              <option :value="1000">1000 条</option>
              <option :value="0">不限制</option>
            </select>
          </div>

          <div>
            <label class="block text-xs text-text-secondary mb-1">时间范围限制</label>
            <select
              v-model.number="appSettings.sync_days"
              class="rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
            >
              <option :value="0">不限制</option>
              <option :value="1">最近 1 天</option>
              <option :value="7">最近 7 天</option>
              <option :value="30">最近 30 天</option>
              <option :value="90">最近 90 天</option>
              <option :value="180">最近 180 天</option>
              <option :value="365">最近 1 年</option>
            </select>
          </div>
        </div>
      </section>

      <button
        class="rounded-lg bg-primary px-4 py-2 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
        :disabled="saving"
        @click="saveSettings"
      >
        {{ saving ? "保存中..." : "保存全部设置" }}
      </button>
    </div>

    <!-- Tab: 关于 -->
    <div v-show="activeTab === '关于'">
      <AboutPanel />
    </div>

    <!-- Add Account / Login Modal -->
    <Teleport to="body">
      <div
        v-if="showAddAccount"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="loginStep === 'idle' && resetLoginState()"
      >
        <div class="w-full max-w-md rounded-xl border border-surface-border bg-surface-2 p-6 shadow-xl">
          <!-- Step 1: 填写凭证 -->
          <template v-if="loginStep === 'idle'">
            <h2 class="text-base font-semibold">添加 Telegram 账户</h2>
            <p class="mt-1 text-xs text-text-muted">
              每个账户需要独立的 API 凭证，前往
              <a href="https://my.telegram.org/apps" target="_blank" class="text-primary underline">my.telegram.org</a>
              获取
            </p>
            <div class="mt-4 space-y-3">
              <div>
                <label class="block text-xs text-text-secondary mb-1">API ID</label>
                <input
                  v-model="newApiId"
                  type="text"
                  placeholder="例如 12345678"
                  class="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary font-mono"
                />
              </div>
              <div>
                <label class="block text-xs text-text-secondary mb-1">API Hash</label>
                <input
                  v-model="newApiHash"
                  type="text"
                  placeholder="32位十六进制字符"
                  class="w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary font-mono"
                />
              </div>
              <div>
                <label class="block text-xs text-text-secondary mb-1">手机号</label>
                <div class="flex gap-2">
                  <CountryCodeSelect v-model="countryCode" />
                  <input
                    v-model="newPhone"
                    type="text"
                    placeholder="手机号码"
                    class="flex-1 rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
                    @keyup.enter="handleAddAccount"
                  />
                </div>
              </div>
            </div>
            <div class="mt-4 flex justify-end gap-2">
              <button
                class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
                @click="resetLoginState"
              >
                取消
              </button>
              <button
                class="rounded-lg bg-primary px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
                :disabled="addingAccount || !newPhone.trim() || !newApiId.trim() || !newApiHash.trim()"
                @click="handleAddAccount"
              >
                {{ addingAccount ? "发送验证码中..." : "发送验证码" }}
              </button>
            </div>
          </template>

          <!-- Step 2: 输入验证码 -->
          <template v-else-if="loginStep === 'code'">
            <h2 class="text-base font-semibold">输入验证码</h2>
            <p class="mt-1 text-xs text-text-muted">
              验证码已发送到 {{ loginAccountId ? (accountsStore.accounts.find(a => a.id === loginAccountId)?.phone || countryCode + newPhone) : countryCode + newPhone }}
            </p>
            <input
              v-model="code"
              type="text"
              placeholder="验证码"
              class="mt-4 w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary text-center tracking-widest text-lg font-mono"
              autofocus
              @keyup.enter="handleVerifyCode"
            />
            <div class="mt-4 flex justify-end gap-2">
              <button
                class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
                @click="resetLoginState"
              >
                取消
              </button>
              <button
                class="rounded-lg bg-primary px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
                :disabled="!code.trim()"
                @click="handleVerifyCode"
              >
                验证
              </button>
            </div>
          </template>

          <!-- Step 3: 两步验证 -->
          <template v-else-if="loginStep === '2fa'">
            <h2 class="text-base font-semibold">两步验证</h2>
            <p class="mt-1 text-xs text-text-muted">该账户开启了两步验证，请输入密码</p>
            <input
              v-model="password2fa"
              type="password"
              placeholder="两步验证密码"
              class="mt-4 w-full rounded-lg border border-surface-border bg-surface px-3 py-2 text-sm outline-none focus:border-primary"
              autofocus
              @keyup.enter="handleVerify2FA"
            />
            <div class="mt-4 flex justify-end gap-2">
              <button
                class="rounded-lg px-3 py-1.5 text-sm text-text-secondary hover:bg-surface cursor-pointer transition-colors"
                @click="resetLoginState"
              >
                取消
              </button>
              <button
                class="rounded-lg bg-primary px-3 py-1.5 text-sm text-white cursor-pointer hover:bg-primary-hover transition-colors disabled:opacity-50"
                :disabled="!password2fa.trim()"
                @click="handleVerify2FA"
              >
                验证
              </button>
            </div>
          </template>

          <p v-if="loginError" class="mt-2 text-xs text-danger">{{ loginError }}</p>
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
            删除后该账户的会话数据将一并清除，确定要删除吗？
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
              @click="accountsStore.deleteAccount(confirmDeleteId!); confirmDeleteId = null"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
