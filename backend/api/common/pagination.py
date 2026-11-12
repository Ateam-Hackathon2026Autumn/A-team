"""一覧APIの共通ページング

Notion の一覧APIの形にそろえる:
    リクエスト: ?page=1&pageSize=20（page は1〜1000000、pageSize は1〜100、初期値 20）
    レスポンス: {"items": [...], "total": 45, "page": 1, "pageSize": 20, "totalPages": 3}

- 範囲外のページ（total を超える page）は 400 にせず、items を空配列で返す
- total と items は同じ時点のデータで数える・取る（transaction.atomic の中で読む。MySQL の初期設定
    REPEATABLE READ では、トランザクション内の読み取りは最初に読んだ時点のスナップショットを見るため。
    読むだけなのでロックはかからない。テストの assertNumQueries では SAVEPOINT と RELEASE の2本が増える）
- 使い方:
    class XxxQuerySerializer(PageQuerySerializer):   # 絞り込みの項目を足す
        status = serializers.ChoiceField(...)

    query = validate_query(XxxQuerySerializer, request)
    return Response(paginate(queryset, query, XxxSerializer))
"""
import math

from django.db import transaction

from rest_framework import serializers

from .serializers import QuerySerializer

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 20


class PageQuerySerializer(QuerySerializer):
    page = serializers.IntegerField(required=False, default=1, min_value=1, max_value=1_000_000)
    page_size = serializers.IntegerField(required=False, default=DEFAULT_PAGE_SIZE, min_value=1,
                                            max_value=MAX_PAGE_SIZE)


def validate_query(serializer_class, request):
    """クエリパラメーターを検証して validated_data を返す（不正なら 400）"""
    serializer = serializer_class(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return serializer.validated_data


def paginate(queryset, query, item_serializer_class, context=None, count_queryset=None):
    """queryset を1ページ分に切り出して、Notion の一覧の形の dict を返す

    - queryset は並び順（order_by）を決めてから渡す。件数は count() で1回、中身は1回の SQL で取る
    - queryset に集計（Count など）を付けているときは、集計を付ける前の queryset を count_queryset に渡す
        （件数を数えるだけなのに JOIN と集計をしないようにするため）
    """
    page, page_size = query["page"], query["page_size"]
    with transaction.atomic():
        total = (count_queryset if count_queryset is not None else queryset).count()
        start = (page - 1) * page_size
        rows = list(queryset[start:start + page_size]) if start < total else []
    return {
        "items": item_serializer_class(rows, many=True, context=context or {}).data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size),
    }
