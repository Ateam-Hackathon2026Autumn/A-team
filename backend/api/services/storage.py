"""ファイルの保存とURL

view から呼ぶ業務ロジック。複数のAPI・バッチで同じ処理を使うものをここにまとめる。

書くもの:
  - 公開画像: images/{user_id}/ランダム。キーが images/自分のID/ で始まるかの検証もここ
  - 非公開: documents/{user_id}/ランダム（申請書類）、chat/{thread_id}/ランダム（チャット添付）
  - 非公開ファイルは表示のたびに期限付きURL（5分 = settings.PRIVATE_FILE_URL_EXPIRE）

使う場所:
  - POST /uploads/images
  - 生産者申請
  - チャット
  - 管理者の申請詳細
"""
