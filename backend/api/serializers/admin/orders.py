"""管理者向け注文管理APIのシリアライザー

対象API:
    GET  /api/v1/admin/orders
    GET  /api/v1/admin/orders/:orderId
    POST /api/v1/admin/orders/:orderId/cancel
    POST /api/v1/admin/orders/:orderId/refund

注文一覧・詳細・キャンセル・返金処理で使用する。
既存のDBモデル・テーブル定義は変更しない。
"""

from rest_framework import serializers

from api.common.serializers import StrictSerializer


class AdminOrderCancelSerializer(StrictSerializer):
    """管理者による注文キャンセルのリクエストを検証する。

    POST /api/v1/admin/orders/:orderId/cancel

    リクエスト:
        {
            "shipmentIds": [2012, 2013],
            "reason": "購入者からキャンセル依頼があったため"
        }

    shipmentIds:
        キャンセル対象となる配送箱IDのリスト。
        1件以上指定し、同じIDを重複して指定できない。

    reason:
        キャンセル理由。空文字・空白のみは不可。
    """

    shipment_ids = serializers.ListField(
        child=serializers.IntegerField(
            min_value=1,
            error_messages={
                "invalid": "配送箱IDは整数で指定してください。",
                "min_value": "配送箱IDは1以上で指定してください。",
            },
        ),
        allow_empty=False,
        error_messages={
            "required": "キャンセル対象の配送箱IDを指定してください。",
            "not_a_list": "配送箱IDはリストで指定してください。",
            "empty": "キャンセル対象の配送箱を1件以上指定してください。",
        },
    )

    reason = serializers.CharField(
        max_length=500,
        allow_blank=False,
        trim_whitespace=True,
        error_messages={
            "required": "キャンセル理由を入力してください。",
            "blank": "キャンセル理由を入力してください。",
            "max_length": "キャンセル理由は500文字以内で入力してください。",
        },
    )

    def validate_shipment_ids(self, value):
        """配送箱IDの重複を確認する。"""
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "同じ配送箱IDを複数指定することはできません。"
            )

        return value


class AdminOrderRefundSerializer(StrictSerializer):
    """管理者による返金処理のリクエストを検証する。

    POST /api/v1/admin/orders/:orderId/refund

    リクエスト:
        {
            "shipmentId": 2012,
            "method": "stripe"
        }

    shipmentId:
        返金対象となる配送箱ID。

    method:
        stripe:
            カード決済に対してStripeで返金する。

        manual:
            銀行振込など、手動で返金したことを記録する。
    """

    shipment_id = serializers.IntegerField(
        min_value=1,
        error_messages={
            "required": "返金対象の配送箱IDを指定してください。",
            "invalid": "配送箱IDは整数で指定してください。",
            "min_value": "配送箱IDは1以上で指定してください。",
        },
    )

    method = serializers.ChoiceField(
        choices=[
            ("stripe", "Stripeによる返金"),
            ("manual", "手動による返金"),
        ],
        error_messages={
            "required": "返金方法を指定してください。",
            "invalid_choice": "返金方法はstripeまたはmanualを指定してください。",
        },
    )


# """注文・返金管理 のシリアライザー

# 使う view: api/views/admin/orders.py

# このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
#   - 注文一覧（管理者）（GET /api/v1/admin/orders）: クエリ・入力の検証とレスポンス
#   - 注文詳細（管理者）（GET /api/v1/admin/orders/:orderId）: クエリ・入力の検証とレスポンス
#   - 注文キャンセル（管理者）（POST /api/v1/admin/orders/:orderId/cancel）: 入力の検証とレスポンス
#   - 返金（POST /api/v1/admin/orders/:orderId/refund）: 入力の検証とレスポンス

# 入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
# """
