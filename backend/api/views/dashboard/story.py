"""ストーリー管理（学ぶページ）

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - ストーリー取得: GET /api/v1/dashboard/story
      ・行がなければ空の内容を返す
  - ストーリー保存: PUT /api/v1/dashboard/story
      ・各項目2,000文字まで。公開には1項目以上。行がなければ作る。就農理由・目標（reason・goal）もここ

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
