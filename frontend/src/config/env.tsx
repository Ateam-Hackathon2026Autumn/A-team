// API のベース URL（未指定なら同一オリジン。開発時は Vite の proxy で /api をバックエンドへ転送）
const VITE_API_URL = import.meta.env.VITE_API_URL ?? '';

// モック使用可否（開発サーバーでは既定で使用。VITE_USE_MOCK=false で本物のバックエンドに接続）
const USE_MOCK =
  import.meta.env.DEV && import.meta.env.VITE_USE_MOCK !== 'false';

export { VITE_API_URL, USE_MOCK };

// 規約本文へのリンクは任意。未設定でも同意チェックによる登録は可能。
function policyUrl(value: string): string {
  try {
    const url = new URL(value.trim());
    return ['https:', 'http:'].includes(url.protocol) ? url.href : '';
  } catch {
    return '';
  }
}
export const TERMS_URL = policyUrl(import.meta.env.VITE_TERMS_URL ?? '');
export const PRIVACY_POLICY_URL = policyUrl(
  import.meta.env.VITE_PRIVACY_POLICY_URL ?? '',
);
