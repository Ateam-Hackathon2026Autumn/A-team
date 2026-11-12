"""送信回数の制限（429 RATE_LIMITED）

ログインの有無にかかわらず、同じIPからの回数で数える。
view に throttle_classes = [IPRateThrottle] と throttle_scope = "signin" のように書いて使う。
回数は settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] の同じ名前の値。

本番でロードバランサー（ALB）の後ろに置くときは、settings.REST_FRAMEWORK["NUM_PROXIES"] を設定して
X-Forwarded-For から本来のIPを取るようにする。
"""
from rest_framework.throttling import SimpleRateThrottle


class IPRateThrottle(SimpleRateThrottle):
    def allow_request(self, request, view):
        self.scope = getattr(view, "throttle_scope", None)
        if not self.scope:
            return True
        self.rate = self.get_rate()
        self.num_requests, self.duration = self.parse_rate(self.rate)
        return super().allow_request(request, view)

    def get_rate(self):
        if not getattr(self, "scope", None):
            return None
        return super().get_rate()

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
