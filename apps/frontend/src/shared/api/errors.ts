export type ApiFieldErrors = Record<string, string | string[]>;

export class ApiError extends Error {
  name = "ApiError";
  status: number;
  code: string;
  fields: ApiFieldErrors;
  requestId?: string;

  constructor(args: {
    status: number;
    code?: string;
    message: string;
    fields?: ApiFieldErrors;
    requestId?: string;
  }) {
    super(args.message);
    this.status = args.status;
    this.code = args.code ?? "UNKNOWN_ERROR";
    this.fields = args.fields ?? {};
    this.requestId = args.requestId;
  }
}

export function parseApiError(status: number, payload: unknown): ApiError {
  if (payload && typeof payload === "object" && "error" in payload) {
    const error = (payload as { error?: Record<string, unknown> }).error ?? {};
    return new ApiError({
      status,
      code: typeof error.code === "string" ? error.code : undefined,
      message:
        typeof error.message === "string"
          ? error.message
          : "Не удалось выполнить запрос. Попробуйте ещё раз.",
      fields:
        error.fields && typeof error.fields === "object"
          ? (error.fields as ApiFieldErrors)
          : undefined,
      requestId: typeof error.request_id === "string" ? error.request_id : undefined,
    });
  }

  return new ApiError({
    status,
    code: status === 429 ? "RATE_LIMITED" : "HTTP_ERROR",
    message:
      status === 401
        ? "Сессия истекла. Войдите снова."
        : status >= 500
          ? "Сервер временно недоступен."
          : "Не удалось выполнить запрос.",
  });
}
