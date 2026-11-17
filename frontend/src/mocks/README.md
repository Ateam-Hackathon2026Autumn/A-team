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
│   ├── store/                       登録・更新を反映するモックのデータと処理（handler から使う）
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

ID などの可変部分は `:` で書く。`body` だけを書いた場合は、どの ID で呼ばれても同じ内容を返す。

```ts
path: '/api/v1/dashboard/products/:productId',
```

`body` だけを書いた場合、クエリ文字列（`?category=1` など）は無視される（絞り込み結果は再現しない）。

### 登録・更新を反映するモック（handler）

ID・クエリ・リクエスト本文に応じて返す内容を変えるモックは、`body` の代わりに `handler(url, init)` を書く。
戻り値は `{ status, body, headers }`（`headers` はレスポンスヘッダーを返す場合だけ）。

一覧・詳細・登録・更新・削除で同じデータを使うものは、データと処理を `rest/store/` にまとめている。
データは同じタブのセッション（sessionStorage）に保存されるため、再読み込みしても変更が残る（タブを閉じると初期状態に戻る）。

| データ | ストア | 主な内容 |
| ------ | ------ | -------- |
| ダッシュボードの商品 | `rest/store/dashboardProducts.tsx` | 一覧・詳細・登録・更新・在庫・削除。etag が更新ごとに変わり、古い etag は 412 |
| ダッシュボードの体験 | `rest/store/dashboardExperiences.tsx` | 体験・予約枠・申込者。一覧は publishStatus、申込者は slotId・status で絞り込み。体験の ETag はヘッダーで返す |
| カート | `rest/endpoint/get_api_v1_cart.tsx` | 追加・数量変更・削除 |

初期データに戻したい場合は、開発者ツールの Application → Session Storage から `tsunagaru-marche.mock-` で始まる項目を削除して再読み込みする。

---

### レスポンスを変える

`rest/endpoint/` の該当ファイルの `status` と `body` を書き換える。
`handler` のあるモックも、`status` を 400 以上にすると handler を使わずに `body` を返す（エラー画面の確認用）。
エラー時のレスポンス例などは、各ファイルのコメントに書いてある。

例：未ログイン状態を確認したい場合は `get_api_v1_auth_session.tsx` の body を
`{ authenticated: false, user: null }` に変更する。

### エンドポイントを追加

1. `rest/endpoint/` に上記のルールでファイルを作成
2. `rest/index.tsx` に1行追加
