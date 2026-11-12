# Bedrock 写真解析：フロント・バック共有サンプル

写真を JSON で送り、Claude Haiku 4.5 が読み取った内容を表示する参考実装です。
`frontend/` が React + Vite、`backend/handler.py` が Python の AWS Lambda ハンドラーです。
ハッカソン本体の `frontend/`・`backend/` への組み込みは、各担当が必要な処理を参照して行えます。

```text
S3 から配信した React → Lambda Function URL → Bedrock Claude Haiku 4.5
                           ↓
                    JSON を返して画面表示
```

通信フロー、リクエスト・レスポンス、制限は [API.md](API.md) を参照してください。

## Git に上げるもの

**この `examples/bedrock-photo/` フォルダ一式を共有対象にします。**

```text
examples/bedrock-photo/
├── .gitignore
├── README.md
├── API.md
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── public/
│   │   ├── config.json          # 空の接続先を持つ共通設定
│   │   └── favicon.svg
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── api.ts
│       └── styles.css
└── backend/
    ├── .env.example            # 環境変数の項目だけを共有
    ├── handler.py
    └── tests/test_handler.py
```

`package-lock.json` も共有し、各担当が同じ依存関係をインストールできるようにします。
`.gitignore` は `node_modules/`、`dist/`、ローカル認証情報、Terraform state / plan 等を除外します。
このリポジトリではルートの設定が `README.md` を除外するため、このサンプル内だけで共有対象へ戻しています。

`infra/test/bedrock-photo/` にある `access.local.json`、実環境の `terraform/`、`build/`、デプロイ診断記録は共有用サンプルに含めていません。元のテスト環境全体の ignore を解除する必要はありません。

リポジトリのルートから対象を確認・ステージする例:

```bash
git ls-files --others --exclude-standard -- examples/bedrock-photo/
git add -- examples/bedrock-photo/
git diff --cached --stat
```

## コードの読み方

| 担当 | ファイル | 読むポイント |
|---|---|---|
| フロント | `frontend/src/api.ts` | 写真の縮小・JPEG/Base64 化、認証ヘッダー、API 呼び出し、受信 JSON の検証 |
| フロント | `frontend/src/App.tsx` | パスワード確認、写真選択、解析中・エラー・結果表示の状態管理 |
| フロント | `frontend/src/main.tsx`、`styles.css` | React の起動位置と表示スタイル |
| フロント | `frontend/vite.config.ts` | 開発用のポートと `/api` の転送先 |
| バック | `backend/handler.py` | 認証、画像検証、プロンプト、返却スキーマ、Bedrock 呼び出し、結果の整理 |
| バック | `backend/tests/test_handler.py` | AWS へ通信せずに認証・入力・応答を検証するテスト |

主要な処理には日本語コメントを追加しています。

## フロントをローカルで動かす

必要なものは Node.js・npm と、接続可能な解析 API です。

```bash
cd examples/bedrock-photo/frontend
npm ci
# 接続先は利用する解析 API の URL に置き換える。
export PHOTO_API_PROXY_TARGET='https://YOUR_FUNCTION_ID.lambda-url.ap-northeast-1.on.aws'
npm run dev
```

`http://127.0.0.1:5174` を開き、API 側に設定したテスト用パスワードを入力します。
環境変数は Vite 起動前にシェルで設定します。この設定ファイルは `.env` の値を自動では読み込みません。
接続先を指定しない場合の既定値は `http://127.0.0.1:8787` です。そのポートの API サーバーを起動する処理は、このサンプルには含めていません。API 未接続でもパスワード入力画面までは起動できます。

`public/config.json` の `apiBaseUrl` は共有時には空文字です。開発時は Vite が `/api` を転送します。
S3 等で配信する場合は、ビルド後の `dist/config.json` に利用する HTTPS の Lambda Function URL を設定します。
`dist/` は Git の対象外です。`npm run preview` は本番ビルドを使うため、同様に接続設定が必要です。

```bash
npm run build
```

## バックを利用する

`backend/handler.py` は **AWS Lambda 用**です。既存の Django サーバーを起動するコードとは別の参考実装です。

- ランタイム: Python 3.13、ハンドラー: `handler.lambda_handler`
- 配置するコード: `backend/handler.py`（ZIP のルートに `handler.py` を置く）
- 利用する SDK: `boto3`（このサンプルは Lambda の Python ランタイム同梱 SDK を利用）
- 環境変数: `BEDROCK_MODEL_ID`、`API_TOKEN_SHA256`。項目は `.env.example` にあります。
- Lambda の IAM ロール: 対象の推論プロファイル・全推論先モデルへの `bedrock:InvokeModel` と、CloudWatch Logs 出力の権限が必要です。
- API 入口: Lambda Function URL。今回の方式ではハンドラーが共有パスワードを検証します。別 origin のブラウザから呼ぶ場合は、Function URL の CORS も設定します。
- このサンプルのデプロイ用 Terraform は含めていません。既存の配置・モデル利用可否・権限設定はインフラ担当と合わせます。

パスワードのハッシュを手元で生成する例（入力文字列を表示・コードへ埋め込みしない）:

```bash
python3 -c 'import getpass, hashlib; print(hashlib.sha256(getpass.getpass("Test password: ").encode()).hexdigest())'
```

出力したハッシュを Lambda の `API_TOKEN_SHA256` に設定し、パスワードの原文は別途チーム内で共有します。

バックエンドの既存テストを動かす場合は、リポジトリのルートで実行します。

```bash
python3 -m unittest discover -s examples/bedrock-photo/backend/tests -v
```

テストでは SDK を Mock に置き換えるため、AWS 認証や実際のモデル呼び出しは不要です。
