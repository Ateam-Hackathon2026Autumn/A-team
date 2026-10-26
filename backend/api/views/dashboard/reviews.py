"""レビュー確認・返信

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - レビュー一覧（生産者）: GET /api/v1/dashboard/reviews
      ・product_id・未返信だけで絞り込み
  - レビュー返信: POST /api/v1/dashboard/reviews/:reviewId/reply
      ・1,000文字まで。上書き可、空で削除。初めて返信したときだけ投稿者に通知（メールなし）
      ・掲載停止中の生産者は返信不可（409）

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
