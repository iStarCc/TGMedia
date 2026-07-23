<script setup lang="ts">
const props = withDefaults(defineProps<{
  name: string;
  size?: number;
  filled?: boolean;
}>(), { size: 18, filled: false });
</script>

<template>
  <span
    class="material-symbols-rounded inline-flex items-center justify-center select-none leading-none"
    aria-hidden="true"
    :style="{
      fontSize: `${props.size}px`,
      width: `${props.size}px`,
      height: `${props.size}px`,
      fontVariationSettings: props.filled ? `'FILL' 1` : `'FILL' 0`,
    }"
  >{{ props.name }}</span>
</template>
