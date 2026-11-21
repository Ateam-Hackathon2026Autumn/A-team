"""API 共通のミドルウェア"""
from django.http import JsonResponse

HEALTH_PATH = "/api/health/"


class HealthCheckMiddleware:
    """GET /api/health/ には、ホスト名を確かめずにすぐ 200 を返す

    ALB のヘルスチェックは Host にコンテナの IP アドレスを入れて送ってくるので、
    ALLOWED_HOSTS で確かめると 400 になり「異常」と判定されてしまう。
    ほかの URL は今までどおり ALLOWED_HOSTS で確かめる（このミドルウェアは一番先に置く）
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == HEALTH_PATH and request.method in ("GET", "HEAD"):
            return JsonResponse({"status": "ok", "service": "backend"}, headers={"Cache-Control": "no-store"})
        return self.get_response(request)



class NoStoreMiddleware:
    """/api/ のレスポンスすべてに Cache-Control: no-store を付ける（認証・個人情報をキャッシュさせない）"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
        return response
