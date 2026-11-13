"""生産者ダッシュボード のシリアライザー

使う view: api/views/dashboard/summary.py

  - 生産者ダッシュボード（GET /api/v1/dashboard/summary）: クエリなし（何か付けたら400）。レスポンスは view で dict を作る
"""
from ...common.serializers import QuerySerializer


class SummaryQuerySerializer(QuerySerializer):
    """クエリは受け付けない"""
