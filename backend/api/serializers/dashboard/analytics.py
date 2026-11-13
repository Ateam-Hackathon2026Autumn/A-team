"""生産者ダッシュボードの分析のシリアライザー"""
from rest_framework import serializers

class AnalyticsQuerySerializer(serializers.Serializer):
  """分析APIのクエリパラメータを検証する
  
  GET  /api/v1/dashboard/analytics
  
  クエリ:
       year: 集計対象年（省略時はView側で現在年を設定する）
  """

  year = serializers.IntegerField(
    required=False,
    min_value=2000,
    max_value=2100,
    error_messages={
      "invalid": "年は整数で指定してください。",
      "min_value": "年は2000以上で指定してください。",
      "max_value": "年は2100以下で指定してください。",
    },
  )

class AnalyticsMonthlySerializer(serializers.Serializer):
  """月毎の注文数・売上のレスポンス"""

  month = serializers.IntegerField(min_value=1, max_value=12)
  order_count = serializers.IntegerField(min_value=0)
  sales = serializers.IntegerField(min_value=0)


class AnalyticsTopProductSerializer(serializers.Serializer):
  """販売数上位商品のレスポンス"""

  product_id = serializers.IntegerField(min_value=1)
  product_name = serializers.CharField()
  quantity = serializers.IntegerField(min_value=0)


class AnalyticsResponseSerializer(serializers.Serializer):
  """分析APIのレスポンス形式"""

  year = serializers.IntegerField(min_value=2000, max_value=2100)
  monthly = AnalyticsMonthlySerializer(many=True)
  top_products = AnalyticsTopProductSerializer(many=True)
  favorite_count = serializers.IntegerField(min_value=0)



#使う view: api/views/dashboard/analytics.py

#このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
 # - 分析（生産者）（GET /api/v1/dashboard/analytics）: クエリ・入力の検証とレスポンス

#入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる

