# A-team

## 使用技術

| 技術 | バージョン |
| --- | --- |
| React | 19.3 |
| Vite | 8.3 |
| TypeScript | 6.0 |
| Tailwind CSS | 4.3 |
| Node.js | 24 LTS |
| Python | 3.13 |
| Django | 5.2 LTS |
| mysqlclient | 2.3 |
| MySQL | 8.4 LTS |
| Docker Compose | v2 |
| Pillow13.0 |
| django-storages 1.14.6 |
| boto3 1.43.115 |

## 起動手順

Docker Desktopを起動してから、以下を実行してください。

```bash
git clone https://github.com/Ateam-Hackathon2026Autumn/A-team.git
cd A-team
cp .env.example .env
docker compose up --build -d
docker compose exec backend python manage.py createsuperuser # 初回のみ実行
```


- フロントエンド: <http://localhost:5173>
- Django API: <http://localhost:8000/api/health/>
- Django管理画面: <http://localhost:8000/admin/>

### 開発用のデータ

画面の確認に使うデータ（会員・生産者・商品・体験・求人・注文・レビュー）をまとめて入れます。カテゴリーと都道府県のマスタも一緒に入ります。

```bash
docker compose exec backend python manage.py seed_dev          # 入れる（何回実行しても増えません）
docker compose exec backend python manage.py seed_dev --reset  # 開発用のデータだけ消して入れ直す
```

| メールアドレス | 内容 |
| --- | --- |
| buyer1@example.com | 会員（注文・予約・応募・カートあり） |
| buyer2@example.com | 会員（購入なし） |
| applicant@example.com | 会員（生産者申請が審査中） |
| producer1@example.com | 生産者・山本農園（公開中） |
| producer2@example.com | 生産者・海風水産（公開中） |
| producer3@example.com | 生産者・牧ファーム（掲載停止中） |

パスワードは全員 `MarcheDev#2026` です（開発環境でだけ作られます）。

商品・生産者・体験の写真は `backend/marche/seed_images/` のもの（AI で作った確認用の画像）を使います。

画像は、`AWS_STORAGE_BUCKET_NAME` を設定していなければ `backend/media/` に保存され、<http://localhost:8000/media/> から表示されます（S3 の設定は不要です）。

フロントを本物の API につなぐには、`frontend/.env.development.local` に `VITE_USE_MOCK=false` と書いて `docker compose restart frontend` を実行します。
