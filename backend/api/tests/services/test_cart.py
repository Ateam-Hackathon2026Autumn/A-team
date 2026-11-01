"""api/services/cart.py の単体テスト"""
from django.test import TestCase

from marche.models import CartItem

from ...services.cart import merge_guest_cart
from ..utils import make_product, make_user


class MergeGuestCartTests(TestCase):
    def setUp(self):
        self.user = make_user()
        self.other = make_user(email="other@example.com")
        self.carrot = make_product(name="にんじん")
        self.onion = make_product(name="たまねぎ")

    def test_moves_items_and_sums_same_product_up_to_10(self):
        CartItem.objects.create(user=self.user, product=self.carrot, quantity=7)
        CartItem.objects.create(session_key="guest", product=self.carrot, quantity=6)
        CartItem.objects.create(session_key="guest", product=self.onion, quantity=1)

        self.assertEqual(merge_guest_cart("guest", self.user), 2)
        cart = {i.product_id: i.quantity for i in CartItem.objects.filter(user=self.user)}
        self.assertEqual(cart, {self.carrot.id: 10, self.onion.id: 1})
        self.assertFalse(CartItem.objects.filter(session_key="guest").exists())

    def test_other_sessions_and_users_are_untouched(self):
        CartItem.objects.create(session_key="another-guest", product=self.carrot, quantity=1)
        CartItem.objects.create(user=self.other, product=self.carrot, quantity=3)
        merge_guest_cart("guest", self.user)
        self.assertEqual(CartItem.objects.filter(session_key="another-guest").count(), 1)
        self.assertEqual(CartItem.objects.get(user=self.other).quantity, 3)

    def test_no_session_key(self):
        self.assertEqual(merge_guest_cart(None, self.user), 0)
