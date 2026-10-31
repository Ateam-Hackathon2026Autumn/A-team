"""管理者向け の URL

api/urls/__init__.py から /api/v1/admin/ に include する。

ここに並べる view:
  - api/views/admin/auth.py
  - api/views/admin/summary.py
  - api/views/admin/producer_applications.py
  - api/views/admin/contents.py
  - api/views/admin/users.py
  - api/views/admin/inquiries.py
  - api/views/admin/reports.py
  - api/views/admin/orders.py
  - api/views/admin/announcements.py
  - api/views/admin/analytics.py
  - api/views/admin/admins.py
  - api/views/admin/audit_logs.py

パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする
"""
