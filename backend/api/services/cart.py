"""カートの持ち主の判定と付け替え

- 会員は user_id、ゲストは session_key でカートを引く
- ログイン・新規登録時に、ゲストのときの session_key の行を user_id に付け替える
  （同じ商品は数量を合算し、上限10で切り捨てる）

使う場所: GET・POST・PATCH・DELETE /cart、POST /auth/signin、POST /users、POST /orders（カートを空にする）
"""
from django.db import transaction

from marche.models import CartItem

MAX_QUANTITY = 10


def merge_guest_cart(guest_session_key, user):
    """ゲストのカートを会員のカートに付け替える。

    Django の login() はセッションキーを作り直すので、呼び出し側は login() の前に
    request.session.session_key を控えておき、login() の後にこの関数を呼ぶ。
    戻り値は付け替えた（または合算した）行数。
    """
    if not guest_session_key:
        return 0

    with transaction.atomic():
        guest_items = list(
            CartItem.objects.select_for_update().filter(session_key=guest_session_key, user__isnull=True)
        )
        if not guest_items:
            return 0

        member_items = {
            item.product_id: item
            for item in CartItem.objects.select_for_update().filter(
                user=user, product_id__in=[g.product_id for g in guest_items]
            )
        }

        for guest in guest_items:
            member = member_items.get(guest.product_id)
            if member:
                # 同じ商品が会員のカートにもある：数量を合算（上限10）してゲスト側の行を消す
                member.quantity = min(member.quantity + guest.quantity, MAX_QUANTITY)
                member.save(update_fields=["quantity", "updated_at"])
                guest.delete()
            else:
                guest.user = user
                guest.session_key = None
                guest.save(update_fields=["user", "session_key", "updated_at"])

    return len(guest_items)
