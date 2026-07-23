import { computed } from "vue";

export function useDownloadProgress(downloaded: () => number, total: () => number) {
  const progress = computed(() => {
    const t = total();
    if (t <= 0) return 0;
    return Math.min(downloaded() / t, 1);
  });

  const percent = computed(() => Math.round(progress.value * 100));

  return { progress, percent };
}
