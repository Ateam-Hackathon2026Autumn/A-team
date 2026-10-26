"""送信回数の制限

書くもの:
  - 同じIPから1時間5回まで（429）
  - 対象: POST /inquiries、POST /auth/password-reset
  - レートは settings.REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] の inquiry・password_reset
"""
