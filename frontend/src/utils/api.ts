import { useErrorDialogStore } from "@/stores/errorDialog";
import { readApiError } from "@/utils/apiError";

const BASE = import.meta.env.BASE_URL.replace(/\/$/, "");

export function apiUrl(path: string): string {
  return `${BASE}${path}`;
}

export function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(apiUrl(path), init);
}

export async function apiFetchOrThrow(path: string, init?: RequestInit): Promise<Response> {
  const res = await apiFetch(path, init);
  if (!res.ok) throw await readApiError(res);
  return res;
}

export async function downloadApiFile(path: string, filename: string): Promise<boolean> {
  const errorDialog = useErrorDialogStore();
  try {
    const res = await apiFetch(path);
    if (!res.ok) throw await readApiError(res);

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
    return true;
  } catch (err) {
    errorDialog.showError(err, "下载失败");
    return false;
  }
}
