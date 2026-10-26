"""画像キーを表示用URLにする

書くもの:
  - DB に保存した S3 のキー → default_storage.url(key)。キーが空なら None
  - 公開画像は署名なしURL（settings.AWS_QUERYSTRING_AUTH = False）
"""
