# A-team

## 使用技術

| 技術 | バージョン | 選定理由 |
| --- | --- | --- |
| React | 19.3 | 現行の安定版で、ViteのReact構成と互換性があるため |
| Vite | 8.3 | 高速な開発サーバーとビルド環境を利用できるため |
| TypeScript | 6.0 | Vite 8の公式テンプレートで採用されている安定版のため |
| Tailwind CSS | 4.3 | Viteプラグインで簡単に導入でき、設定が少ないため |
| Node.js | 24 LTS | Viteを動かせる長期サポート版のため |
| Python | 3.13 | Django 5.2が正式対応する安定版のため |
| Django | 5.2 LTS | 長期サポート対象で、セキュリティ更新を受けられるため |
| mysqlclient | 2.3 | Python 3.13からMySQLへ接続できる安定版のため |
| MySQL | 8.4 LTS | 長期サポート対象で、仕様変更が少ないため |
| Docker Compose | v2 | チーム全員で同じ開発環境を再現できるため |

## 起動手順

Docker Desktopを起動してから、以下を実行してください。

```bash
git clone https://github.com/Ateam-Hackathon2026Autumn/A-team.git
cd A-team
cp .env.example .env
docker compose up --build
```

- フロントエンド: <http://localhost:5173>
- Django API: <http://localhost:8000/api/health/>
- Django管理画面: <http://localhost:8000/admin/>
