// API呼び出し失敗時に投げる独自エラー
class ApiError extends Error {
  status: number;
  // 入力不正（400）のときの項目ごとのメッセージ（例: { name: ['商品名を入力してください。'] }）
  details: Record<string, string[]>;

  constructor(
    status: number,
    message: string,
    details: Record<string, string[]> = {},
  ) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

// エラーレスポンス（{ errorCode, errorMsg, details? }）から ApiError を作る
// 本文を読めない場合は fallback のメッセージにする
async function toApiError(
  response: Response,
  fallback: string,
): Promise<ApiError> {
  try {
    const { errorMsg, details } = (await response.json()) as {
      errorMsg?: string;
      details?: Record<string, string[]>;
    };

    return new ApiError(response.status, errorMsg ?? fallback, details);
  } catch {
    return new ApiError(response.status, fallback);
  }
}

export default ApiError;
export { toApiError };
