"""画像アップロード

認証: 会員

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 画像アップロード: POST /api/v1/uploads/images
      ・jpg・png・サイズ上限。公開用の場所に images/{user_id}/ランダム で保存 → services/storage.py
      ・S3 のキーと表示用URLを返す。DB には書かない
      ・キーを保存する側のAPIで「images/自分のID/ で始まるか」を検証する

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
