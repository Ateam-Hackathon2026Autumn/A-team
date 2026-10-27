import { USE_MOCK } from '../config/env';

/**
 * モック有効時の初期化（src/main.tsx から1度だけ呼ぶ）
 */
function setupMock(): void {
  if (!USE_MOCK) {
    return;
  }

  console.info(
    '%c[mock]%c モック使用中（バックエンドに接続なし）',
    'background:#2f6b4f;color:#fff;padding:2px 6px;border-radius:4px;font-weight:bold',
    'color:inherit',
  );
  console.info(
    [
      '  APIの応答を変える      : src/mocks/rest/endpoint/ (エンドポイントごとのファイル)',
      '  本物のバックエンドに繋ぐ: VITE_USE_MOCK=false を指定して再起動（src/mocks/README.md）',
    ].join('\n'),
  );
}

export { setupMock };
