<script setup lang="ts">
import MIcon from "@/components/common/MIcon.vue";

defineProps<{
  label: string;
  value: string | number;
  trend?: string;
  icon?: string;
  color?: string;
}>();
</script>

<template>
  <div
    class="group relative rounded-xl border border-surface-border bg-surface-2 p-5 transition-all duration-200 hover:border-primary/30"
  >
    <div class="flex items-start justify-between">
      <div>
        <p class="text-xs font-medium text-text-muted tracking-wide">
          {{ label }}
        </p>
        <p class="mt-2 text-xl font-semibold tracking-tight font-mono">
          {{ value }}
        </p>
        <p v-if="trend" class="mt-1.5 text-xs text-text-muted">{{ trend }}</p>
      </div>
      <div
        v-if="icon"
        class="flex h-9 w-9 items-center justify-center rounded-lg transition-colors"
        :class="color || 'bg-primary/10 text-primary'"
      >
        <MIcon :name="icon" :size="18" />
      </div>
    </div>
  </div>
</template>
