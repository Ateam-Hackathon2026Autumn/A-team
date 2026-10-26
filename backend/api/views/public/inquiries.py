"""問い合わせ

認証: ゲスト可

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 問い合わせ送信: POST /api/v1/inquiries
      ・同じIPから1時間5回まで（429）→ common/throttles.py
      ・order_id はログイン中の会員の自分の注文だけ
      ・受付メールを自動送信。CSRF を明示的に確認

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
