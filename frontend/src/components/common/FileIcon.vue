<script setup lang="ts">
import { computed } from "vue";
import MIcon from "@/components/common/MIcon.vue";

const props = defineProps<{ type: string }>();

const iconName = computed(() => {
  const map: Record<string, string> = {
    video: "video_file",
    photo: "image",
    audio: "audio_file",
    document: "description",
  };
  return map[props.type] || "description";
});

const iconColor = computed(() => {
  const map: Record<string, string> = {
    video: "text-info",
    photo: "text-primary",
    audio: "text-warning",
    document: "text-text-secondary",
  };
  return map[props.type] || "text-text-secondary";
});
</script>

<template>
  <MIcon :name="iconName" :size="20" :class="iconColor" />
</template>
