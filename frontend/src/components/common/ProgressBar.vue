<script setup lang="ts">
defineProps<{
  progress: number;
  status?: string;
}>();
</script>

<template>
  <div class="h-1.5 w-full rounded-full bg-surface-border overflow-hidden">
    <div
      class="h-full rounded-full transition-all duration-500 ease-out"
      :class="[
        status === 'downloading' && 'bg-info',
        status === 'completed' && 'bg-emerald-500',
        status === 'paused' && 'bg-warning',
        status === 'failed' && 'bg-danger',
        status === 'pending' && 'bg-text-muted',
      ]"
      :style="{ width: `${Math.min(progress * 100, 100)}%` }"
    />
  </div>
</template>
