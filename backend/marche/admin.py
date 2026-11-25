"""Django 標準の管理画面（/api/django-admin/）に出すテーブル

データの確認（発表での説明・開発中の確認）に使う。データの修正は、在庫・公開の条件・掲載停止などのルールを
確かめる API を使うこと。この画面は API のチェックを通らずに DB を直接書き換えるため、次のようにしている。

- どのテーブルも削除はできない（注文などがまとめて消えるのを防ぐ）
- 注文・箱・明細・体験の予約・操作ログ・通知は見るだけ（お金と履歴の記録なので）
- DB が計算する列（割引後の価格 sale_price・評価など）は読み取り専用

本番では環境変数 DJANGO_ADMIN_ENABLED=true のときだけ開ける（config/urls.py）。
"""
from django.contrib import admin

from .models import (
    ApplicationDocument,
    Area,
    AuditLog,
    Category,
    Experience,
    ExperienceImage,
    ExperienceReview,
    ExperienceSlot,
    Inquiry,
    InquiryNote,
    Job,
    JobApplication,
    JobWorkDate,
    Notice,
    Notification,
    Order,
    OrderItem,
    OrderShipment,
    Prefecture,
    Producer,
    ProducerApplication,
    ProducerImage,
    ProducerStory,
    Product,
    ProductImage,
    ProductReview,
    Report,
    Reservation,
    ShippingSetting,
    User,
)

admin.site.site_header = "つながるマルシェ 管理画面（データ確認用）"
admin.site.site_title = "つながるマルシェ 管理画面"
admin.site.index_title = "テーブル一覧"
# 一覧画面の「選択した〜を削除」を出さない
admin.site.disable_action("delete_selected")

TIMESTAMPS = ("created_at", "updated_at")


class MarcheAdmin(admin.ModelAdmin):
    """共通：削除はできない。作成・更新日時は読み取り専用"""

    readonly_fields = TIMESTAMPS
    list_per_page = 50

    def has_delete_permission(self, request, obj=None):
        return False


class ViewOnlyAdmin(MarcheAdmin):
    """見るだけ（追加・変更・削除はできない）"""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class MarcheInline(admin.TabularInline):
    extra = 0
    readonly_fields = TIMESTAMPS

    def has_delete_permission(self, request, obj=None):
        return False


class ViewOnlyInline(MarcheInline):
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


# =========================================================
# 会員・マスタ
# =========================================================

@admin.register(User)
class UserAdmin(MarcheAdmin):
    list_display = ("id", "email", "last_name", "first_name", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("email", "last_name", "first_name", "phone")
    ordering = ("-id",)
    fields = ("email", "last_name", "first_name", "phone", "birth_date", "prefecture", "interests", "profile_image",
              "is_active", "is_staff", "is_superuser", "groups", "password", "last_login", "date_joined",
              "email_verified_at", "deleted_at", "updated_at")
    # パスワードはハッシュの表示だけ（変更はパスワード再設定の API で）
    readonly_fields = ("password", "last_login", "date_joined", "email_verified_at", "deleted_at", "updated_at")
    filter_horizontal = ("groups",)

    def has_add_permission(self, request):
        # 会員は新規登録の API、運営は create_admin・運営の API で作る
        return False


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sort_order")

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Prefecture)
class PrefectureAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "area")
    list_filter = ("area",)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "sort_order")

    def has_delete_permission(self, request, obj=None):
        return False


# =========================================================
# 生産者
# =========================================================

class ProducerImageInline(MarcheInline):
    model = ProducerImage


class ShippingSettingInline(MarcheInline):
    model = ShippingSetting


@admin.register(Producer)
class ProducerAdmin(MarcheAdmin):
    list_display = ("id", "business_name", "representative_name", "genre", "prefecture", "career_start_year",
                    "accepts_experience", "recruiting", "approval_status", "publish_status")
    list_filter = ("genre", "approval_status", "publish_status", "accepts_experience", "recruiting", "prefecture")
    search_fields = ("business_name", "representative_name", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = TIMESTAMPS + ("featured_score", "stripe_account_id")
    inlines = (ShippingSettingInline, ProducerImageInline)


class ApplicationDocumentInline(MarcheInline):
    model = ApplicationDocument


@admin.register(ProducerApplication)
class ProducerApplicationAdmin(MarcheAdmin):
    list_display = ("id", "producer", "status", "submitted_at", "reviewed_at", "reviewer")
    list_filter = ("status",)
    search_fields = ("producer__business_name", "producer__user__email")
    raw_id_fields = ("producer", "reviewer")
    inlines = (ApplicationDocumentInline,)


@admin.register(ProducerStory)
class ProducerStoryAdmin(MarcheAdmin):
    list_display = ("id", "producer", "publish_status", "updated_at")
    list_filter = ("publish_status",)
    search_fields = ("producer__business_name",)
    raw_id_fields = ("producer",)


# =========================================================
# 商品・注文・レビュー
# =========================================================

class ProductImageInline(MarcheInline):
    model = ProductImage


@admin.register(Product)
class ProductAdmin(MarcheAdmin):
    list_display = ("id", "name", "producer", "category", "price", "discount_rate", "sale_price", "stock",
                    "publish_status", "rating_avg", "review_count")
    list_filter = ("publish_status", "category", "is_subscription", "is_preorder")
    search_fields = ("name", "producer__business_name")
    raw_id_fields = ("producer", "shipping_setting")
    # sale_price は DB が price と discount_rate から計算する（生成列）。評価・人気はバッチ・レビューで計算する
    readonly_fields = TIMESTAMPS + ("sale_price", "popularity_score", "rating_avg", "review_count")
    inlines = (ProductImageInline,)


class OrderShipmentInline(ViewOnlyInline):
    model = OrderShipment
    fields = ("producer", "temperature_zone", "shipping_fee", "status", "tracking_no", "shipped_at",
              "refunded_amount")
    readonly_fields = fields


@admin.register(Order)
class OrderAdmin(ViewOnlyAdmin):
    list_display = ("id", "order_no", "ordered_at", "buyer", "payment_method", "payment_status", "items_total",
                    "shipping_total", "grand_total")
    list_filter = ("payment_status", "payment_method")
    search_fields = ("order_no", "user__email", "guest_email", "ship_name")
    date_hierarchy = "ordered_at"
    exclude = ("access_token_hash",)
    inlines = (OrderShipmentInline,)

    @admin.display(description="購入者")
    def buyer(self, order):
        return order.user.email if order.user_id else f"ゲスト（{order.guest_email}）"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user")


class OrderItemInline(ViewOnlyInline):
    model = OrderItem
    fields = ("product_name", "unit_price", "discount_rate", "paid_unit_price", "quantity", "tax_rate", "subtotal")
    readonly_fields = fields


@admin.register(OrderShipment)
class OrderShipmentAdmin(ViewOnlyAdmin):
    list_display = ("id", "order", "producer", "temperature_zone", "status", "shipping_fee", "shipped_at",
                    "refunded_amount")
    list_filter = ("status", "temperature_zone")
    search_fields = ("order__order_no", "producer__business_name", "tracking_no")
    inlines = (OrderItemInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("order", "producer")


@admin.register(ProductReview)
class ProductReviewAdmin(MarcheAdmin):
    list_display = ("id", "product", "user", "rating", "created_at", "replied_at")
    list_filter = ("rating",)
    search_fields = ("product__name", "user__email", "body")
    raw_id_fields = ("order_item", "product", "user")


# =========================================================
# 体験
# =========================================================

class ExperienceImageInline(MarcheInline):
    model = ExperienceImage


class ExperienceSlotInline(MarcheInline):
    model = ExperienceSlot
    readonly_fields = TIMESTAMPS + ("reserved_count",)


@admin.register(Experience)
class ExperienceAdmin(MarcheAdmin):
    list_display = ("id", "title", "producer", "prefecture", "price_adult", "price_child", "family_ok",
                    "publish_status")
    list_filter = ("publish_status", "family_ok", "beginner_ok", "prefecture")
    search_fields = ("title", "producer__business_name")
    raw_id_fields = ("producer",)
    inlines = (ExperienceSlotInline, ExperienceImageInline)


@admin.register(Reservation)
class ReservationAdmin(ViewOnlyAdmin):
    list_display = ("id", "reservation_no", "slot", "user", "adult_count", "child_count", "total_amount", "status")
    list_filter = ("status",)
    search_fields = ("reservation_no", "user__email", "representative_name")


@admin.register(ExperienceReview)
class ExperienceReviewAdmin(MarcheAdmin):
    list_display = ("id", "experience", "user", "rating", "created_at")
    list_filter = ("rating",)
    raw_id_fields = ("reservation", "experience", "user")


# =========================================================
# 求人
# =========================================================

class JobWorkDateInline(MarcheInline):
    model = JobWorkDate


@admin.register(Job)
class JobAdmin(MarcheAdmin):
    list_display = ("id", "title", "producer", "term_type", "pay_unit", "pay_amount", "slots", "publish_status")
    list_filter = ("publish_status", "term_type", "pay_unit", "inexperienced_ok")
    search_fields = ("title", "producer__business_name")
    raw_id_fields = ("producer",)
    inlines = (JobWorkDateInline,)


@admin.register(JobApplication)
class JobApplicationAdmin(MarcheAdmin):
    list_display = ("id", "job", "user", "status", "created_at", "decided_at")
    list_filter = ("status",)
    search_fields = ("job__title", "user__email")
    raw_id_fields = ("job", "user")


# =========================================================
# 運営（問い合わせ・通報・お知らせ・操作ログ・通知）
# =========================================================

class InquiryNoteInline(MarcheInline):
    model = InquiryNote
    raw_id_fields = ("author",)


@admin.register(Inquiry)
class InquiryAdmin(MarcheAdmin):
    list_display = ("id", "subject", "category", "status", "priority", "user", "email", "created_at")
    list_filter = ("status", "category", "priority")
    search_fields = ("subject", "email", "body")
    raw_id_fields = ("user", "order", "assignee")
    inlines = (InquiryNoteInline,)


@admin.register(Report)
class ReportAdmin(MarcheAdmin):
    list_display = ("id", "target_type", "target_id", "reason", "status", "reporter", "created_at")
    list_filter = ("status", "target_type", "reason")
    raw_id_fields = ("reporter", "handled_by")


@admin.register(Notice)
class NoticeAdmin(MarcheAdmin):
    list_display = ("id", "title", "audience", "published_at")
    list_filter = ("audience",)


@admin.register(AuditLog)
class AuditLogAdmin(ViewOnlyAdmin):
    list_display = ("id", "created_at", "admin", "action", "target_type", "target_id")
    list_filter = ("action", "target_type")


@admin.register(Notification)
class NotificationAdmin(ViewOnlyAdmin):
    list_display = ("id", "user", "notification_type", "title", "read_at", "created_at")
    list_filter = ("notification_type",)
    search_fields = ("user__email", "title")
