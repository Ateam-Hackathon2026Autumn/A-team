// API呼び出し失敗時に投げる独自エラー
class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

export default ApiError;
