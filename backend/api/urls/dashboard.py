"""生産者向け の URL

api/urls/__init__.py から /api/v1/dashboard/ に include する。

ここに並べる view:
  - api/views/dashboard/summary.py
  - api/views/dashboard/profile.py
  - api/views/dashboard/shipping_settings.py
  - api/views/dashboard/products.py
  - api/views/dashboard/orders.py
  - api/views/dashboard/experiences.py
  - api/views/dashboard/jobs.py
  - api/views/dashboard/story.py
  - api/views/dashboard/reviews.py
  - api/views/dashboard/sales.py
  - api/views/dashboard/analytics.py

パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする
"""
