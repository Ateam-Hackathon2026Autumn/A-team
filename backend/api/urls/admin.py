"""管理者向け の URL（/api/v1/admin/...）

api/urls/__init__.py から /api/v1/admin/ に include する。
パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする。

これから並べる view: auth・summary・producer_applications・contents・users・inquiries・reports・
announcements・analytics・admins・audit_logs（api/views/admin/ の同名ファイル）
"""

from django.urls import path

from ..views.admin import orders


urlpatterns = [
    # 注文一覧
    path(
        "orders",
        orders.AdminOrderListView.as_view(),
        name="admin-order-list",
    ),

    # 注文詳細
    path(
        "orders/<int:order_id>",
        orders.AdminOrderDetailView.as_view(),
        name="admin-order-detail",
    ),

    # 注文キャンセル
    path(
        "orders/<int:order_id>/cancel",
        orders.AdminOrderCancelView.as_view(),
        name="admin-order-cancel",
    ),

    # 注文返金
    path(
        "orders/<int:order_id>/refund",
        orders.AdminOrderRefundView.as_view(),
        name="admin-order-refund",
    ),
]
