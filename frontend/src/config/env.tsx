// API のベース URL（未指定なら同一オリジン。開発時は Vite の proxy で /api をバックエンドへ転送）
const VITE_API_URL = import.meta.env.VITE_API_URL ?? '';

// モック使用可否（開発サーバーでは既定で使用。VITE_USE_MOCK=false で本物のバックエンドに接続）
const USE_MOCK =
  import.meta.env.DEV && import.meta.env.VITE_USE_MOCK !== 'false';

export { VITE_API_URL, USE_MOCK };

// バックエンドの稼働環境の版番号と、公開済みの本文 URL を設定する。
export const TERMS_VERSION = (import.meta.env.VITE_TERMS_VERSION ?? '').trim();
export const PRIVACY_POLICY_VERSION = (import.meta.env.VITE_PRIVACY_POLICY_VERSION ?? '').trim();
export const TERMS_URL = (import.meta.env.VITE_TERMS_URL ?? '').trim();
export const PRIVACY_POLICY_URL = (import.meta.env.VITE_PRIVACY_POLICY_URL ?? '').trim();
function isPolicyUrl(value: string): boolean {
  try {
    return ['https:', 'http:'].includes(new URL(value).protocol);
  } catch {
    return false;
  }
}
export const SIGNUP_POLICY_CONFIGURED = Boolean(
  TERMS_VERSION && PRIVACY_POLICY_VERSION && isPolicyUrl(TERMS_URL) && isPolicyUrl(PRIVACY_POLICY_URL),
);
