"""管理者向け の URL（/api/v1/admin/...）

api/urls/__init__.py から /api/v1/admin/ に include する。
パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする。

（view は api/views/admin/ の同名ファイル）
"""

from django.urls import path

from ..views.admin import (admins, analytics, announcements, audit_logs, auth, contents, inquiries, orders,
                           producer_applications, reports, summary, users)



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

    # ユーザー管理
    path("users", users.AdminUserListView.as_view(), name="admin-users"),
    path("users/<int:user_id>", users.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("users/<int:user_id>/status", users.AdminUserStatusView.as_view(), name="admin-user-status"),

    # 問い合わせ・通報
    path("inquiries", inquiries.AdminInquiryListView.as_view(), name="admin-inquiries"),
    path("inquiries/<int:inquiry_id>", inquiries.AdminInquiryDetailView.as_view(), name="admin-inquiry-detail"),
    path("reports", reports.AdminReportListView.as_view(), name="admin-reports"),
    path("reports/<int:report_id>", reports.AdminReportDetailView.as_view(), name="admin-report-detail"),

    # お知らせ・管理者アカウント・操作ログ・分析
    path("announcements", announcements.AdminAnnouncementListView.as_view(), name="admin-announcements"),
    path("announcements/<int:announcement_id>", announcements.AdminAnnouncementDetailView.as_view(),
         name="admin-announcement-detail"),
    path("admins", admins.AdminStaffListView.as_view(), name="admin-admins"),
    path("admins/<int:admin_id>", admins.AdminStaffDetailView.as_view(), name="admin-admin-detail"),
    path("audit-logs", audit_logs.AdminAuditLogListView.as_view(), name="admin-audit-logs"),
    path("analytics", analytics.AdminAnalyticsView.as_view(), name="admin-analytics"),

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
