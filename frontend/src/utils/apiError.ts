export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function readApiError(res: Response): Promise<ApiError> {
  const message = await parseApiErrorMessage(res);
  return new ApiError(message, res.status);
}

export async function parseApiErrorMessage(res: Response): Promise<string> {
  try {
    const data = await res.json();
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item: { msg?: string; message?: string }) => item.msg || item.message || String(item))
        .join("；");
    }
  } catch {
    /* 非 JSON 响应 */
  }
  if (res.status === 404) return "请求的资源不存在";
  if (res.status >= 500) return "服务器错误，请稍后重试";
  return `请求失败 (${res.status})`;
}

export function errorTitle(status?: number): string {
  if (status === 404) return "资源不存在";
  if (status === 403) return "无权访问";
  if (status === 401) return "未授权";
  if (status && status >= 500) return "服务器错误";
  return "操作失败";
}
