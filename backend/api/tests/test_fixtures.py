"""初期データ（marche/fixtures）が読み込めることのテスト

  - python manage.py loaddata prefectures: エリア7件・都道府県47件（ID は JIS コード）
"""
from django.core.management import call_command
from django.test import TestCase

from marche.models import Area, Prefecture


class PrefectureFixtureTests(TestCase):
    def test_load(self):
        call_command("loaddata", "prefectures", verbosity=0)
        self.assertEqual(Area.objects.count(), 7)
        self.assertEqual(Prefecture.objects.count(), 47)
        self.assertEqual(Prefecture.objects.get(pk=13).name, "東京都")
        self.assertEqual(Prefecture.objects.get(name="沖縄県").area.name, "九州・沖縄")
        self.assertEqual(list(Area.objects.order_by("sort_order").values_list("name", flat=True)),
                         ["北海道", "東北", "関東", "中部", "近畿", "中国・四国", "九州・沖縄"])
