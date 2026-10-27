// API のベース URL（未指定なら同一オリジン。開発時は Vite の proxy で /api をバックエンドへ転送）
const VITE_API_URL = import.meta.env.VITE_API_URL ?? '';

// モック使用可否（開発サーバーでは既定で使用。VITE_USE_MOCK=false で本物のバックエンドに接続）
const USE_MOCK =
  import.meta.env.DEV && import.meta.env.VITE_USE_MOCK !== 'false';

export { VITE_API_URL, USE_MOCK };
