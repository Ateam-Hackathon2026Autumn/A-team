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
