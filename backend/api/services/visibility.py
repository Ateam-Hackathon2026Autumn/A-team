"""公開側に表示してよいかの条件（QuerySet）

公開側のAPI・お気に入り・カート・注文の購入可否で、同じ条件を使うためにここにまとめる。

- 生産者: approval_status=approved かつ publish_status=public
          かつ ログインアカウント（users）が有効（is_active=True）で未退会（deleted_at が空）
- 商品・体験・求人・ストーリー: 自身の publish_status=public かつ 生産者が上の条件を満たす
- 生産者を掲載停止すると、商品などの状態は変えなくても公開側から消える
- ユーザーの条件は保険（退会・利用停止では生産者も suspended にするが、利用停止の「再開」では生産者の状態を
  戻さないため、is_active だけが変わった状態がありうる）

使い方:
    public_products()                          # 公開中の商品
    public_content(Experience.objects.all())   # 体験・求人など、producer を持つ QuerySet
    public_producers()                         # 公開中の生産者
"""
from django.db.models import Q

from marche.models import Producer, Product, PublishStatus


def public_producer_q(prefix=""):
    """公開中の生産者の条件（Q）。商品から見るときは prefix="producer__" を付ける"""
    return Q(**{
        f"{prefix}approval_status": Producer.ApprovalStatus.APPROVED,
        f"{prefix}publish_status": PublishStatus.PUBLIC,
        f"{prefix}user__is_active": True,
        f"{prefix}user__deleted_at__isnull": True,
    })


def public_producers():
    """公開中の生産者"""
    return Producer.objects.filter(public_producer_q())


def public_content(queryset):
    """producer を持つ QuerySet（商品・体験・求人・ストーリー）を、公開してよいものだけに絞る"""
    return queryset.filter(Q(publish_status=PublishStatus.PUBLIC) & public_producer_q("producer__"))


def public_products():
    """公開中の商品"""
    return public_content(Product.objects.all())
