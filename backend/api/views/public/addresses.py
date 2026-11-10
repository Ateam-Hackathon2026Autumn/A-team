"""お届け先（住所録）

認証: 会員（未ログインは 401）。メール未確認でも使える
仕様: api-spec.md「7. 実装で決めたこと」ステップ7a（Notion には名前だけ）。カラム名: claude/er-diagram.md

実装済み:
  - お届け先一覧: GET /api/v1/users/me/addresses
      ・{items: [...]}（ページングなし。最大10件）。いつも使う住所（isDefault）を先頭に、あとは新しい順
  - お届け先登録: POST /api/v1/users/me/addresses
      ・10件まで（超えたら 409 ADDRESS_LIMIT_EXCEEDED）。201 で登録した1件
      ・1件目は自動でいつも使う住所にする。isDefault=true なら、ほかの住所の印を外す
  - お届け先更新: PATCH /api/v1/users/me/addresses/:addressId
      ・送った項目だけ。isDefault=true にしたら、ほかの住所の印を外す
      ・いつも使う住所の isDefault を false にするのは 400（ほかの住所を true にしてもらう）。200 で更新した1件
  - お届け先削除: DELETE /api/v1/users/me/addresses/:addressId
      ・204。いつも使う住所を消したら、残りのうち一番新しい住所をいつも使う住所にする
  - 他人の住所・存在しない住所は 404 ADDRESS_NOT_FOUND

同時更新: 自分の住所の行をまとめてロック（select_for_update）してから件数・いつも使う住所を確かめる
（2件同時に登録しても、上限を超えたり、いつも使う住所が2つになったりしないように）
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from marche.models import Address, User

from ...common.exceptions import ApiError, Conflict
from ...serializers.public.addresses import AddressCreateSerializer, AddressSerializer, AddressUpdateSerializer

MAX_ADDRESSES = 10
MAX_ID = 2 ** 63 - 1


def address_not_found():
    return ApiError(status.HTTP_404_NOT_FOUND, "ADDRESS_NOT_FOUND", "お届け先が見つかりません。")


def lock_addresses(user):
    """自分の住所を新しい順にロックして返す。住所が0件でもロックできるよう、先に会員の行をロックする"""
    User.objects.select_for_update().filter(pk=user.pk).first()
    return list(Address.objects.select_for_update().filter(user=user).order_by("-created_at", "-id"))


def clear_other_defaults(user, keep_id):
    Address.objects.filter(user=user, is_default=True).exclude(pk=keep_id).update(
        is_default=False, updated_at=timezone.now())


def address_response(address_id, status_code=status.HTTP_200_OK):
    address = Address.objects.select_related("prefecture").get(pk=address_id)
    return Response(AddressSerializer(address).data, status=status_code)


class AddressListView(APIView):
    """GET・POST /api/v1/users/me/addresses"""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        addresses = (Address.objects.filter(user=request.user).select_related("prefecture")
                     .order_by("-is_default", "-created_at", "-id"))
        return Response({"items": AddressSerializer(addresses, many=True).data})

    def post(self, request):
        serializer = AddressCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            existing = lock_addresses(request.user)
            if len(existing) >= MAX_ADDRESSES:
                raise Conflict("ADDRESS_LIMIT_EXCEEDED", f"お届け先は{MAX_ADDRESSES}件まで登録できます。")
            data["is_default"] = data["is_default"] or not existing
            address = Address.objects.create(user=request.user, **data)
            if address.is_default:
                clear_other_defaults(request.user, address.pk)
        return address_response(address.pk, status.HTTP_201_CREATED)


class AddressDetailView(APIView):
    """PATCH・DELETE /api/v1/users/me/addresses/:addressId"""

    permission_classes = [IsAuthenticated]

    def find_locked(self, request, address_id):
        addresses = lock_addresses(request.user)
        address = next((a for a in addresses if a.pk == address_id), None) if address_id <= MAX_ID else None
        if address is None:
            raise address_not_found()
        return address, addresses

    def patch(self, request, address_id):
        serializer = AddressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            address, _ = self.find_locked(request, address_id)
            if address.is_default and data.get("is_default") is False:
                raise serializers.ValidationError(
                    {"is_default": ["いつも使うお届け先を変えるときは、ほかのお届け先を選んでください。"]})
            for field, value in data.items():
                setattr(address, field, value)
            address.save()
            if address.is_default:
                clear_other_defaults(request.user, address.pk)
        return address_response(address.pk)

    def delete(self, request, address_id):
        with transaction.atomic():
            address, addresses = self.find_locked(request, address_id)
            address.delete()
            if address.is_default:
                remaining = [a for a in addresses if a.pk != address_id]
                if remaining:  # 新しい順に並んでいるので先頭が一番新しい
                    Address.objects.filter(pk=remaining[0].pk).update(is_default=True, updated_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)
