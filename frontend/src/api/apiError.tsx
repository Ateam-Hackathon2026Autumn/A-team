// API呼び出し失敗時に投げる独自エラー
class ApiError extends Error {
  status: number;
  errorCode?: string;
  // 入力不正（400）のときの項目ごとのメッセージ（例: { name: ['商品名を入力してください。'] }）
  details: Record<string, string[]>;

  constructor(
    status: number,
    message: string,
    details: Record<string, string[]> = {},
    errorCode?: string,
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
    this.errorCode = errorCode;
  }
}

// エラーレスポンス（{ errorCode, errorMsg, details? }）から ApiError を作る
// 本文を読めない場合は fallback のメッセージにする
async function toApiError(
  response: Response,
  fallback: string,
): Promise<ApiError> {
  try {
    const { errorMsg, details, errorCode } = (await response.json()) as {
      errorMsg?: string;
      errorCode?: string;
      details?: Record<string, string[]>;
    };

    return new ApiError(response.status, errorMsg ?? fallback, details, errorCode);
  } catch {
    return new ApiError(response.status, fallback);
  }
}

export default ApiError;
export { toApiError };
