"""公開・会員・ゲスト向け の URL

api/urls/__init__.py から /api/v1/ に include する。

ここに並べる view:
  - api/views/public/auth.py
  - api/views/public/users.py
  - api/views/public/addresses.py
  - api/views/public/notifications.py
  - api/views/public/announcements.py
  - api/views/public/uploads.py
  - api/views/public/catalog.py
  - api/views/public/producers.py
  - api/views/public/cart.py
  - api/views/public/orders.py
  - api/views/public/webhooks.py
  - api/views/public/experiences.py
  - api/views/public/jobs.py
  - api/views/public/favorites.py
  - api/views/public/reviews.py
  - api/views/public/chat.py
  - api/views/public/inquiries.py
  - api/views/public/reports.py
  - api/views/public/producer_applications.py

パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする
"""
