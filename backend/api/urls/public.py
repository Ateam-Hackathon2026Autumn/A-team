"""公開・会員・ゲスト向け の URL

api/urls/__init__.py から /api/v1/ に include する。
パスは api-spec.md のとおり（末尾スラッシュなし）。:id は <int:...> にする
"""
from django.urls import path

from ..views.public import (auth, cart, catalog, favorites, orders, producer_applications, producers, uploads, users,
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
    path("users", users.SignupView.as_view(), name="users-signup"),

    # 商品・カテゴリー
    path("products", catalog.ProductListView.as_view(), name="products-list"),
    path("products/<int:product_id>", catalog.ProductDetailView.as_view(), name="products-detail"),
    path("categories", catalog.CategoryListView.as_view(), name="categories-list"),

    # 生産者・学ぶ
    path("producers", producers.ProducerListView.as_view(), name="producers-list"),
    path("producers/<int:producer_id>", producers.ProducerProfileView.as_view(), name="producers-profile"),
    path("producers/<int:producer_id>/story", producers.ProducerStoryView.as_view(), name="producers-story"),

    # カート
    path("cart", cart.CartView.as_view(), name="cart"),
    path("cart/items", cart.CartItemListView.as_view(), name="cart-items"),
    path("cart/items/<int:item_id>", cart.CartItemDetailView.as_view(), name="cart-item"),

    # 注文・決済
    path("orders", orders.OrderCreateView.as_view(), name="orders-create"),
    path("guest/orders", orders.GuestOrderCreateView.as_view(), name="guest-orders-create"),
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

    # 画像アップロード
    path("uploads/images", uploads.ImageUploadView.as_view(), name="uploads-images"),
]
