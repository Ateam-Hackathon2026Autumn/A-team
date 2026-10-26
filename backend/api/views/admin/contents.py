"""生産者・商品・体験・求人・ストーリーの管理（掲載停止・再開）

認証: 管理者（権限グループ: 審査担当・管理者）
共通: 管理者APIの共通チェック（is_staff と権限グループ）は common/permissions.py、データ変更はすべて services/audit.py で audit_logs に記録

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 一覧（resource = producers・products・experiences・jobs・stories）: GET /api/v1/admin/{resource}
      ・キーワード・publish_status（商品などは producer_id も）で絞り込み。下書きや停止中も表示
  - 詳細: GET /api/v1/admin/{resource}/:id
      ・stories は producer_stories が対象（:id は producer_stories.id）
  - 掲載停止・再開: PATCH /api/v1/admin/{resource}/:id/status
      ・action（suspend・resume）。suspend は reason 必須で publish_status=suspended、生産者に通知とメール
      ・resume は private に戻す（生産者が確認してから自分で公開）
      ・生産者を止めても商品などの状態は変えない

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
