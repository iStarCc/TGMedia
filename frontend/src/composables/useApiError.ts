import { useErrorDialogStore } from "@/stores/errorDialog";

export function useApiError() {
  const errorDialog = useErrorDialogStore();

  async function withErrorHandling<T>(
    fn: () => Promise<T>,
    opts?: { title?: string; fallback?: string },
  ): Promise<T | null> {
    try {
      return await fn();
    } catch (err) {
      errorDialog.showError(err, opts?.fallback ?? "操作失败", { title: opts?.title });
      return null;
    }
  }

  return {
    showError: errorDialog.showError.bind(errorDialog),
    withErrorHandling,
  };
}
