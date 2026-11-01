"""API 共通のミドルウェア"""


class NoStoreMiddleware:
    """/api/ のレスポンスすべてに Cache-Control: no-store を付ける（認証・個人情報をキャッシュさせない）"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
        return response
