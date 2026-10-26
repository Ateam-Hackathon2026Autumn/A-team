"""ゲストも使うAPIの CSRF 確認

書くもの:
  - DRF の SessionAuthentication は未ログインのリクエストに CSRF を確認しないため、ゲストも使うAPIでは明示的に確認する
  - 対象: カート・注文・ゲスト注文キャンセル・問い合わせ・新規登録・ログイン・パスワード再設定
  - Webhook（POST /webhooks/stripe）は対象外
"""
