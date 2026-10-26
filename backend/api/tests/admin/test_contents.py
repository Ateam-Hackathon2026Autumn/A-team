"""生産者・商品・体験・求人・ストーリーの管理（掲載停止・再開） のテスト

テスト対象: api/views/admin/contents.py

確認すること（シーケンス図の opt 分岐ごとに1テストを目安にする）:
  - 一覧（resource = producers・products・experiences・jobs・stories）: GET /api/v1/admin/{resource}
      ・キーワード・publish_status（商品などは producer_id も）で絞り込み。下書きや停止中も表示
  - 詳細: GET /api/v1/admin/{resource}/:id
      ・stories は producer_stories が対象（:id は producer_stories.id）
  - 掲載停止・再開: PATCH /api/v1/admin/{resource}/:id/status
      ・action（suspend・resume）。suspend は reason 必須で publish_status=suspended、生産者に通知とメール
      ・resume は private に戻す（生産者が確認してから自分で公開）
      ・生産者を止めても商品などの状態は変えない

S3 には接続しない（override_settings で STORAGES を FileSystemStorage にする）
"""
