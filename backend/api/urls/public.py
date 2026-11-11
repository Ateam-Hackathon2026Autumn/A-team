"""公開・会員・ゲスト向け の URL

api/urls/__init__.py から /api/v1/ に include する。
パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする
"""
from django.urls import path

from ..views.public import (addresses, announcements, auth, cart, catalog, experiences, favorites, inquiries, jobs,
                            notifications, orders, producer_applications, producers, reports, reviews, uploads, users,
                            webhooks)

urlpatterns = [
    # 認証・ユーザー
    path("auth/csrf", auth.CsrfView.as_view(), name="auth-csrf"),
    path("auth/signin", auth.SigninView.as_view(), name="auth-signin"),
    path("auth/session", auth.SessionView.as_view(), name="auth-session"),
    path("auth/signout", auth.SignoutView.as_view(), name="auth-signout"),
    path("auth/email-verification/resend", auth.EmailVerificationResendView.as_view(),
        name="auth-email-verification-resend"),
    path("auth/email-verification/confirm", auth.EmailVerificationConfirmView.as_view(),
        name="auth-email-verification-confirm"),
    path("auth/password-reset", auth.PasswordResetView.as_view(), name="auth-password-reset"),
    path("auth/password-reset/confirm", auth.PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("users", users.SignupView.as_view(), name="users-signup"),
    path("users/me", users.MeView.as_view(), name="users-me"),
    path("users/me/email", users.EmailChangeView.as_view(), name="users-me-email"),
    path("users/me/password", users.PasswordChangeView.as_view(), name="users-me-password"),
    path("users/me/addresses", addresses.AddressListView.as_view(), name="addresses"),
    path("users/me/addresses/<int:address_id>", addresses.AddressDetailView.as_view(), name="address-detail"),
    path("users/me/notification-settings", notifications.NotificationSettingView.as_view(),
         name="notification-settings"),

    # 通知・お知らせ
    path("notifications", notifications.NotificationListView.as_view(), name="notifications"),
    path("notifications/unread-count", notifications.NotificationUnreadCountView.as_view(),
         name="notifications-unread-count"),
    path("notifications/read-all", notifications.NotificationReadAllView.as_view(), name="notifications-read-all"),
    path("notifications/<int:notification_id>/read", notifications.NotificationReadView.as_view(),
         name="notification-read"),
    path("announcements", announcements.AnnouncementListView.as_view(), name="announcements"),
    path("announcements/<int:announcement_id>", announcements.AnnouncementDetailView.as_view(),
         name="announcement-detail"),

    # 商品・カテゴリー
    path("products", catalog.ProductListView.as_view(), name="products-list"),
    path("products/<int:product_id>", catalog.ProductDetailView.as_view(), name="products-detail"),
    path("products/<int:product_id>/reviews", reviews.ProductReviewListCreateView.as_view(), name="product-reviews"),
    path("users/me/reviews/<int:review_id>", reviews.MyReviewDetailView.as_view(), name="my-review"),
    path("categories", catalog.CategoryListView.as_view(), name="categories-list"),

    # 生産者・学ぶ
    path("producers", producers.ProducerListView.as_view(), name="producers-list"),
    path("producers/<int:producer_id>", producers.ProducerProfileView.as_view(), name="producers-profile"),
    path("producers/<int:producer_id>/story", producers.ProducerStoryView.as_view(), name="producers-story"),

    # カート
    path("cart", cart.CartView.as_view(), name="cart"),
    path("cart/items", cart.CartItemListView.as_view(), name="cart-items"),
    path("cart/items/<int:item_id>", cart.CartItemDetailView.as_view(), name="cart-item"),

    # 体験
    path("experiences", experiences.ExperienceListView.as_view(), name="experiences-list"),
    path("experiences/<int:experience_id>", experiences.ExperienceDetailView.as_view(), name="experiences-detail"),
    path("experiences/<int:experience_id>/applications", experiences.ExperienceApplicationCreateView.as_view(),
         name="experience-applications"),
    path("users/me/experience-applications", experiences.MyExperienceApplicationListView.as_view(),
         name="my-experience-applications"),
    path("users/me/experience-applications/<int:application_id>/cancel",
         experiences.MyExperienceApplicationCancelView.as_view(), name="my-experience-application-cancel"),

    # 求人
    path("jobs", jobs.JobListView.as_view(), name="jobs-list"),
    path("jobs/<int:job_id>", jobs.JobDetailView.as_view(), name="jobs-detail"),
    path("jobs/<int:job_id>/applications", jobs.JobApplicationCreateView.as_view(), name="job-applications"),
    path("users/me/job-applications", jobs.MyJobApplicationListView.as_view(), name="my-job-applications"),
    path("users/me/job-applications/<int:application_id>/withdraw", jobs.MyJobApplicationWithdrawView.as_view(),
         name="my-job-application-withdraw"),

    # 注文・決済
    path("orders", orders.OrderCreateView.as_view(), name="orders-create"),
    path("guest/orders", orders.GuestOrderCreateView.as_view(), name="guest-orders-create"),
    path("orders/<int:order_id>", orders.GuestOrderDetailView.as_view(), name="guest-order-detail"),
    path("orders/<int:order_id>/cancel", orders.GuestOrderCancelView.as_view(), name="guest-order-cancel"),
    path("users/me/orders", orders.MyOrderListView.as_view(), name="my-orders"),
    path("users/me/orders/<int:order_id>", orders.MyOrderDetailView.as_view(), name="my-order-detail"),
    path("users/me/orders/<int:order_id>/cancel", orders.MyOrderCancelView.as_view(), name="my-order-cancel"),
    path("webhooks/stripe", webhooks.StripeWebhookView.as_view(), name="webhooks-stripe"),

    # お気に入り
    path("users/me/favorites", favorites.FavoriteListView.as_view(), name="favorites-list"),
    path("users/me/favorites/products/<int:product_id>", favorites.FavoriteProductView.as_view(),
         name="favorites-product"),
    path("users/me/favorites/producers/<int:producer_id>", favorites.FavoriteProducerView.as_view(),
         name="favorites-producer"),

    # 生産者申請
    path("producer-applications", producer_applications.ProducerApplicationCreateView.as_view(),
         name="producer-applications"),
    path("producer-applications/me", producer_applications.MyProducerApplicationView.as_view(),
         name="producer-applications-me"),

    # 問い合わせ・通報
    path("inquiries", inquiries.InquiryCreateView.as_view(), name="inquiries"),
    path("reports", reports.ReportCreateView.as_view(), name="reports"),

    # 画像アップロード
    path("uploads/images", uploads.ImageUploadView.as_view(), name="uploads-images"),
]
