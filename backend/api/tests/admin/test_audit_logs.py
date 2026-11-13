"""操作ログ のテスト

テスト対象: api/views/admin/audit_logs.py
  - 操作ログ一覧: GET /api/v1/admin/audit-logs（adminId・action・targetType・targetId・期間。新しい順）
"""
from datetime import datetime

from django.utils import timezone

from marche.models import AuditLog

from ..utils import ApiTestCase
from .test_producer_applications import make_staff

BASE = "/api/v1/admin/audit-logs"


def log(admin, action, target_type, target_id, at):
    entry = AuditLog.objects.create(admin=admin, action=action, target_type=target_type, target_id=target_id,
                                    detail={"reason": "x"})
    AuditLog.objects.filter(pk=entry.pk).update(created_at=at)
    return entry


class AdminAuditLogTests(ApiTestCase):
    def test_list(self):
        me = make_staff("admin@example.com", "管理者")
        cs = make_staff("cs@example.com", "CS")
        jst = timezone.make_aware
        first = log(me, "suspend", "product", 1, jst(datetime(2026, 11, 1, 0, 30)))
        second = log(cs, "refund", "order_shipment", 5, jst(datetime(2026, 11, 2, 23, 59)))
        third = log(me, "resume", "product", 1, jst(datetime(2026, 11, 3, 9)))
        self.signin(me.email)
        data = self.client.get(BASE).json()
        self.assertEqual([i["id"] for i in data["items"]], [third.id, second.id, first.id])
        self.assertEqual(data["items"][1]["admin"], {"id": cs.id, "name": "審査 花子"})
        for query, expected in [({"adminId": cs.id}, [second.id]), ({"action": "suspend"}, [first.id]),
                                ({"targetType": "product", "targetId": 1}, [third.id, first.id]),
                                ({"startDate": "2026-11-01", "endDate": "2026-11-02"}, [second.id, first.id]),
                                ({"startDate": "2026-11-03"}, [third.id])]:
            self.assertEqual([i["id"] for i in self.client.get(BASE, query).json()["items"]], expected, query)
        for query in [{"startDate": "2026-11-03", "endDate": "2026-11-01"}, {"adminId": 0}, {"startDate": "x"}]:
            self.assertEqual(self.client.get(BASE, query).status_code, 400, query)
        self.post_json("/api/v1/admin/auth/signout")
        self.signin(cs.email)
        self.assertEqual(self.client.get(BASE).status_code, 403)
