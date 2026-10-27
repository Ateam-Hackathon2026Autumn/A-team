// ---------------------------------------------------------------------------
// REST モック(mocks/rest/*)
// ---------------------------------------------------------------------------

// エンドポイント1つ分のモック定義。mocks/rest/endpoint/ の各ファイルがこの形を1つ export する。
//
// 処理は書かず、返したい内容をそのまま書くだけ。
type RestMock = {
  // 'GET' / 'POST' など
  method: string;
  // '/api/v1/users/me' のようなパス
  // ID などの可変部分は '/api/v1/dashboard/products/:productId' のように : で書く
  path: string;
  // 返す HTTP ステータス
  status: number;
  // 返す JSON。204 など本文を持たない応答では書かない
  body?: unknown;
  // このエンドポイントだけ遅らせたいときのミリ秒。
  // 未指定なら mocks/rest/settings.tsx の delayMs が使われる。
  delayMs?: number;
};

export type { RestMock };
