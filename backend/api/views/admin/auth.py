"""管理者ログイン

認証: 公開・ゲスト可

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 管理者ログインチェック: GET /api/v1/admin/auth/session
      ・CSRF Cookie を発行。is_staff でなければ未ログイン扱い。権限グループを返す
  - 管理者ログイン: POST /api/v1/admin/auth/signin
      ・is_staff でないユーザーも「メールアドレスまたはパスワードが違います」の 401
  - 管理者ログアウト: POST /api/v1/admin/auth/signout

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
