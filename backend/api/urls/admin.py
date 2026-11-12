"""管理者向け の URL（/api/v1/admin/...）

api/urls/__init__.py から /api/v1/admin/ に include する。
パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする。

これから並べる view: users・inquiries・reports・announcements・analytics・admins・audit_logs
（api/views/admin/ の同名ファイル）
"""

from django.urls import path

from ..views.admin import auth, contents, orders, producer_applications, summary



def content_paths(resource):
    """掲載の管理（一覧・詳細・掲載停止と再開）の3本"""
    return [
        path(resource, contents.ContentListView.as_view(resource=resource), name=f"admin-{resource}"),
        path(f"{resource}/<int:obj_id>", contents.ContentDetailView.as_view(resource=resource),
             name=f"admin-{resource}-detail"),
        path(f"{resource}/<int:obj_id>/status", contents.ContentStatusView.as_view(resource=resource),
             name=f"admin-{resource}-status"),
    ]


urlpatterns = [
    # 運営ダッシュボード
    path("summary", summary.AdminSummaryView.as_view(), name="admin-summary"),

    # 掲載の管理（生産者・商品・体験・求人・ストーリー）
    *content_paths("producers"),
    *content_paths("products"),
    *content_paths("experiences"),
    *content_paths("jobs"),
    *content_paths("stories"),

    # 管理者ログイン
    path("auth/session", auth.AdminSessionView.as_view(), name="admin-auth-session"),
    path("auth/signin", auth.AdminSigninView.as_view(), name="admin-auth-signin"),
    path("auth/signout", auth.AdminSignoutView.as_view(), name="admin-auth-signout"),

    # 生産者審査
    path("producer-applications", producer_applications.ApplicationListView.as_view(),
         name="admin-producer-applications"),
    path("producer-applications/<int:application_id>", producer_applications.ApplicationDetailView.as_view(),
         name="admin-producer-application-detail"),
    path("producer-applications/<int:application_id>/approve", producer_applications.ApproveView.as_view(),
         name="admin-producer-application-approve"),
    path("producer-applications/<int:application_id>/reject", producer_applications.RejectView.as_view(),
         name="admin-producer-application-reject"),
    path("producer-applications/<int:application_id>/return", producer_applications.ReturnView.as_view(),
         name="admin-producer-application-return"),

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
