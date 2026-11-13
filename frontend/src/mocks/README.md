# モック

バックエンドの実装を待たずにフロントエンドを開発するための、**フロント内で完結するモック**。

- バックエンドも DB も **起動不要**（`npm run dev` だけで動く）
- 本番ビルド（`npm run build`）ではモックは無効になる

レスポンスの形は Notion「設計 → API」の各 API（OpenAPI）に合わせている。
データは全エンドポイントで共通の架空データ（ログインユーザー = 山本農園の山本 健太さん、など）。

---

## 使い方

```sh
cd frontend
npm run dev
```

起動してブラウザのコンソールに次が表示されればモックが有効

```
[mock] モック使用中（バックエンドに接続なし）
```

API を呼ぶたびに `[mock] GET /api/v1/auth/session -> 200` のようにコンソールへ出力される。
**モックは実際の通信を行わないため、DevTools の Network タブには表示されない。**

## 本物のバックエンドに繋ぎたい場合

開発サーバーでは既定でモックを使う（`.env.*` は Git 管理外のため、設定ファイルなしでモックが有効になるようにしている）。
本物のバックエンドに繋ぐ場合は、環境変数 `VITE_USE_MOCK=false` を指定して起動する。

- `npm run dev` で起動している場合

  ```sh
  VITE_USE_MOCK=false npm run dev
  ```

  または `frontend/.env.development.local` に `VITE_USE_MOCK=false` と書いて再起動
  （Vite は起動時にしか環境変数を読み込まないため、変えたら必ず再起動）

- frontend コンテナで起動している場合は、`compose.yaml` の frontend に
  `environment: VITE_USE_MOCK: "false"` を追加して `docker compose up -d frontend`

| 状況                                 | 接続先                                            |
| ------------------------------------ | ------------------------------------------------- |
| `npm run dev`（既定）                | モック                                            |
| `VITE_USE_MOCK=false` を指定して起動 | 本物のバックエンド（Vite の proxy で `/api` を転送） |
| `npm run build`（本番）              | 本物（モックは使われない）                        |

---

## ファイル構成

```
src/mocks/
├── rest/
│   ├── endpoint/                    エンドポイントごとに1ファイル
│   │   ├── get_api_v1_auth_session.tsx               GET   /api/v1/auth/session
│   │   ├── get_api_v1_dashboard_products.tsx         GET   /api/v1/dashboard/products
│   │   ├── patch_api_v1_dashboard_products_productId.tsx
│   │   │                                             PATCH /api/v1/dashboard/products/{productId}
│   │   └── ...
│   ├── settings.tsx                 共通の設定（遅延時間）
│   └── index.tsx                    endpoint/ の一覧（登録するだけ）
├── helpers.tsx                    使用する関数（日付の生成など）
├── types.tsx                      型定義
├── mockFetch.tsx                  rest/ を読んで Response を返す fetch 互換関数（編集不要）
└── index.tsx                      起動バナーの表示（編集不要）
```

普段書き換えるのは `rest/endpoint/` の中のみ
<br />
（共通の設定のみ `rest/settings.tsx`）

### ファイル名のルール

HTTPメソッド + URL を `_` で繋ぐ（先頭の `/` は省略、`{productId}` のような可変部分は波括弧を外す）

| API                                            | ファイル                                                   |
| ---------------------------------------------- | ---------------------------------------------------------- |
| `GET /api/v1/auth/session`                     | `rest/endpoint/get_api_v1_auth_session.tsx`                |
| `PATCH /api/v1/dashboard/products/{productId}` | `rest/endpoint/patch_api_v1_dashboard_products_productId.tsx` |

### パスの書き方

ID などの可変部分は `:` で書く。どの ID で呼ばれても同じ内容を返す。

```ts
path: '/api/v1/dashboard/products/:productId',
```

クエリ文字列（`?category=1` など）は無視される（絞り込み結果は再現しない）。

---

### レスポンスを変える

`rest/endpoint/` の該当ファイルの `status` と `body` を書き換える。
エラー時のレスポンス例などは、各ファイルのコメントに書いてある。

例：未ログイン状態を確認したい場合は `get_api_v1_auth_session.tsx` の body を
`{ authenticated: false, user: null }` に変更する。

### エンドポイントを追加

1. `rest/endpoint/` に上記のルールでファイルを作成
2. `rest/index.tsx` に1行追加
