"""通報

認証: 会員

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 通報: POST /api/v1/reports
      ・target_type（product・experience・job・story・producer・user）
      ・同じ対象を何度でも通報できる
      ・user は生産者がやり取りの相手を通報する場合だけ

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
