import { defineStore } from "pinia";
import { ref } from "vue";
import { ApiError, errorTitle } from "@/utils/apiError";

export const useErrorDialogStore = defineStore("errorDialog", () => {
  const visible = ref(false);
  const title = ref("操作失败");
  const message = ref("");

  function show(msg: string, opts?: { title?: string }) {
    message.value = msg;
    title.value = opts?.title ?? "操作失败";
    visible.value = true;
  }

  function showError(err: unknown, fallback = "操作失败", opts?: { title?: string }) {
    if (err instanceof ApiError) {
      show(err.message, { title: opts?.title ?? errorTitle(err.status) });
      return;
    }
    if (err instanceof Error && err.message) {
      show(err.message, { title: opts?.title ?? fallback });
      return;
    }
    show(fallback, { title: opts?.title ?? fallback });
  }

  function close() {
    visible.value = false;
  }

  return { visible, title, message, show, showError, close };
});
