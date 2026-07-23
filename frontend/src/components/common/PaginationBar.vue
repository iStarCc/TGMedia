<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  total: number;
  currentPage: number;
  pageSize: number;
  unit?: string;
}>();

const emit = defineEmits<{
  "update:currentPage": [page: number];
  "update:pageSize": [size: number];
  change: [];
}>();

const pageSizeOptions = [
  { value: 20, label: "20" },
  { value: 50, label: "50" },
  { value: 100, label: "100" },
  { value: 200, label: "200" },
  { value: 500, label: "500" },
  { value: 1000, label: "1000" },
  { value: 0, label: "全部" },
];

const totalPages = computed(() => {
  if (props.pageSize === 0) return 1;
  return Math.max(1, Math.ceil(props.total / props.pageSize));
});

const visiblePages = computed(() => {
  const total = totalPages.value;
  if (total <= 7) {
    return Array.from({ length: total }, (_, i) => i + 1);
  }
  let start = Math.max(1, props.currentPage - 3);
  let end = Math.min(total, start + 6);
  start = Math.max(1, end - 6);
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
});

const showPagination = computed(() => props.pageSize > 0 && totalPages.value > 1);

function goToPage(page: number) {
  const p = Math.min(Math.max(1, page), totalPages.value);
  if (p === props.currentPage) return;
  emit("update:currentPage", p);
  emit("change");
}

function onPageSizeChange() {
  emit("update:currentPage", 1);
  emit("change");
}
</script>

<template>
  <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div class="flex items-center gap-2 text-xs text-text-muted">
      <span>每页</span>
      <select
        :value="pageSize"
        class="rounded-lg border border-surface-border bg-surface px-2 py-1 text-xs outline-none focus:border-primary cursor-pointer"
        @change="emit('update:pageSize', Number(($event.target as HTMLSelectElement).value)); onPageSizeChange()"
      >
        <option v-for="opt in pageSizeOptions" :key="opt.label" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
      <span>共 {{ total }} 个{{ unit || "" }}</span>
    </div>

    <div v-if="showPagination" class="flex flex-wrap items-center justify-end gap-1">
      <button
        class="rounded px-2 py-1 text-xs cursor-pointer transition-colors"
        :class="currentPage === 1 ? 'text-text-muted/50 cursor-not-allowed' : 'text-text-secondary hover:bg-surface hover:text-text-primary'"
        :disabled="currentPage === 1"
        @click="goToPage(1)"
      >
        首页
      </button>
      <button
        class="rounded px-2 py-1 text-xs cursor-pointer transition-colors"
        :class="currentPage === 1 ? 'text-text-muted/50 cursor-not-allowed' : 'text-text-secondary hover:bg-surface hover:text-text-primary'"
        :disabled="currentPage === 1"
        @click="goToPage(currentPage - 1)"
      >
        上一页
      </button>
      <button
        v-for="p in visiblePages"
        :key="p"
        class="min-w-7 rounded px-2 py-1 text-xs cursor-pointer transition-colors"
        :class="p === currentPage ? 'bg-primary text-white' : 'text-text-secondary hover:bg-surface hover:text-text-primary'"
        @click="goToPage(p)"
      >
        {{ p }}
      </button>
      <button
        class="rounded px-2 py-1 text-xs cursor-pointer transition-colors"
        :class="currentPage === totalPages ? 'text-text-muted/50 cursor-not-allowed' : 'text-text-secondary hover:bg-surface hover:text-text-primary'"
        :disabled="currentPage === totalPages"
        @click="goToPage(currentPage + 1)"
      >
        下一页
      </button>
      <button
        class="rounded px-2 py-1 text-xs cursor-pointer transition-colors"
        :class="currentPage === totalPages ? 'text-text-muted/50 cursor-not-allowed' : 'text-text-secondary hover:bg-surface hover:text-text-primary'"
        :disabled="currentPage === totalPages"
        @click="goToPage(totalPages)"
      >
        尾页
      </button>
    </div>
  </div>
</template>
