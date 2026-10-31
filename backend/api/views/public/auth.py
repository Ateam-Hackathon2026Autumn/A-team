"""認証（ログイン・ログアウト・パスワード再設定）

認証: 公開・ゲスト可

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - ログインチェック: GET /api/v1/auth/session
      ・CSRF Cookie を発行する（ensure_csrf_cookie）。フロントは画面読み込み時に1回呼ぶ
      ・未ログインでも 200 でログイン状態を返す
      ・停止・退会済み（is_active=False）ならセッションを破棄する
  - ログイン: POST /api/v1/auth/signin
      ・失敗は「メールアドレスまたはパスワードが違います」で 401
      ・停止・退会済みは 403
      ・ログイン前の session_key を控え、セッションを再発行してからゲストのカートを合算して付け替える（同じ商品は数量合算・上限10）→ services/cart.py
      ・CSRF を明示的に確認する（未ログインのリクエストなので DRF は確認しない）→ common/authentication.py
  - ログアウト: POST /api/v1/auth/signout
      ・未ログインでも 204
  - パスワード再設定申請: POST /api/v1/auth/password-reset
      ・登録の有無にかかわらず同じ 200 を返す（登録の有無を推測させない）
      ・PasswordResetTokenGenerator（有効期限1時間 = settings.PASSWORD_RESET_TIMEOUT）
      ・同じIPから1時間5回まで（429）→ common/throttles.py
  - パスワード再設定: POST /api/v1/auth/password-reset/confirm
      ・ユーザーID・トークン・新しいパスワードを受け取る
      ・成功したらそのユーザーの全セッションを削除し、通知メールを送る
      ・管理者の初回パスワード設定にも使う

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
