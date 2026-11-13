"""共通エラー形式

すべてのエラーを次の形で返す（Notion「認証・ユーザーAPI 共通定義 components」の ErrorResponse）:
    {"errorCode": "VALIDATION_ERROR", "errorMsg": "入力内容に誤りがあります。", "details": {"lastName": ["..."]}}

- details は 400（入力エラー）のときだけ付ける
- キーのキャメルケース化はレンダラー（CamelCaseJSONRenderer）が行う
- settings.REST_FRAMEWORK["EXCEPTION_HANDLER"] に exception_handler を登録して使う
- DRF の外で起きる CSRF エラー・404・500 も、下の csrf_failure / not_found / server_error で同じ形にする
"""
import logging

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.db import DatabaseError, OperationalError
from django.http import Http404, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response

logger = logging.getLogger(__name__)

SESSION_CHALLENGE = 'Session realm="api"'


class ApiError(exceptions.APIException):
    """errorCode を指定して返すエラーの基底クラス。

    使い方:
        raise ApiError(status.HTTP_409_CONFLICT, "EMAIL_ALREADY_EXISTS", "このメールアドレスは既に登録されています。")
    """

    def __init__(self, status_code, error_code, error_msg, details=None):
        self.status_code = status_code
        self.error_code = error_code
        self.error_msg = error_msg
        self.details = details
        super().__init__(error_msg)


class Conflict(ApiError):
    """409 状態の衝突（在庫不足・申請済み・ログイン済みなど）"""

    def __init__(self, error_code, error_msg):
        super().__init__(status.HTTP_409_CONFLICT, error_code, error_msg)


class CsrfFailed(exceptions.PermissionDenied):
    """403 CSRF トークンの検証に失敗した。フロントの APIクライアントはこのコードを見て1回だけ再送する"""


# errorCode とメッセージの既定値
VALIDATION_ERROR = ("VALIDATION_ERROR", "入力内容に誤りがあります。")
NOT_AUTHENTICATED = ("NOT_AUTHENTICATED", "ログインしてください。")
CSRF_FAILED = ("CSRF_FAILED", "リクエストを確認できませんでした。再度お試しください。")
FORBIDDEN = ("FORBIDDEN", "この操作を行う権限がありません。")
NOT_FOUND = ("NOT_FOUND", "対象が見つかりません。")
METHOD_NOT_ALLOWED = ("METHOD_NOT_ALLOWED", "このメソッドは使用できません。")
UNSUPPORTED_MEDIA_TYPE = ("UNSUPPORTED_MEDIA_TYPE", "リクエストの形式が正しくありません。")
RATE_LIMITED = ("RATE_LIMITED", "時間をおいて再度お試しください。")
INTERNAL_SERVER_ERROR = ("INTERNAL_SERVER_ERROR", "サーバー内部エラーが発生しました。")
SERVICE_UNAVAILABLE = ("SERVICE_UNAVAILABLE", "現在処理を受け付けられません。時間をおいて再度お試しください。")


def error_body(error_code, error_msg, details=None):
    body = {"error_code": error_code, "error_msg": error_msg}
    if details:
        body["details"] = details
    return body


def flatten_details(detail, prefix=""):
    """DRF の ValidationError.detail を {"項目名": ["メッセージ", ...]} の形にそろえる。

    入れ子の項目は "items.0.quantity" のようにドットでつなぐ。
    項目に紐づかないエラー（non_field_errors）はそのままのキーで返す。
    """
    result = {}
    if isinstance(detail, dict):
        for key, value in detail.items():
            name = f"{prefix}.{key}" if prefix else str(key)
            result.update(flatten_details(value, name))
    elif isinstance(detail, list):
        if all(not isinstance(v, (dict, list)) for v in detail):
            result[prefix or "non_field_errors"] = [str(v) for v in detail]
        else:
            for i, value in enumerate(detail):
                result.update(flatten_details(value, f"{prefix}.{i}" if prefix else str(i)))
    else:
        result[prefix or "non_field_errors"] = [str(detail)]
    return result


def exception_handler(exc, context):
    """DRF の例外をすべて共通エラー形式に変換する"""
    headers = {}

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    if isinstance(exc, ApiError):
        status_code, body = exc.status_code, error_body(exc.error_code, exc.error_msg, exc.details)
    elif isinstance(exc, (exceptions.ValidationError, exceptions.ParseError)):
        details = flatten_details(exc.detail) if isinstance(exc, exceptions.ValidationError) else None
        status_code, body = status.HTTP_400_BAD_REQUEST, error_body(*VALIDATION_ERROR, details)
    elif isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        status_code, body = status.HTTP_401_UNAUTHORIZED, error_body(*NOT_AUTHENTICATED)
        headers["WWW-Authenticate"] = SESSION_CHALLENGE
    elif isinstance(exc, CsrfFailed):
        status_code, body = status.HTTP_403_FORBIDDEN, error_body(*CSRF_FAILED)
    elif isinstance(exc, exceptions.PermissionDenied):
        status_code, body = status.HTTP_403_FORBIDDEN, error_body(*FORBIDDEN)
    elif isinstance(exc, exceptions.NotFound):
        status_code, body = status.HTTP_404_NOT_FOUND, error_body(*NOT_FOUND)
    elif isinstance(exc, exceptions.MethodNotAllowed):
        status_code, body = status.HTTP_405_METHOD_NOT_ALLOWED, error_body(*METHOD_NOT_ALLOWED)
    elif isinstance(exc, exceptions.UnsupportedMediaType):
        status_code, body = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, error_body(*UNSUPPORTED_MEDIA_TYPE)
    elif isinstance(exc, exceptions.Throttled):
        status_code, body = status.HTTP_429_TOO_MANY_REQUESTS, error_body(*RATE_LIMITED)
        headers["Retry-After"] = str(max(1, int(exc.wait or 1)))
    elif isinstance(exc, (OperationalError, DatabaseError)):
        # DB に接続できない・ロック待ちのタイムアウトなどの一時障害
        logger.exception("DB の一時障害")
        status_code, body = status.HTTP_503_SERVICE_UNAVAILABLE, error_body(*SERVICE_UNAVAILABLE)
    elif isinstance(exc, exceptions.APIException):
        status_code, body = exc.status_code, error_body(*INTERNAL_SERVER_ERROR)
    else:
        # 想定外のエラー。内部情報は返さず、ログにだけ残す
        logger.exception("想定外のエラー")
        status_code, body = status.HTTP_500_INTERNAL_SERVER_ERROR, error_body(*INTERNAL_SERVER_ERROR)
      
    if status_code == status.HTTP_401_UNAUTHORIZED:
        # 401 には必ず WWW-Authenticate を付ける（ログイン失敗の INVALID_CREDENTIALS も含む）
        headers["WWW-Authenticate"] = SESSION_CHALLENGE
    return Response(body, status=status_code, headers=headers)


# --- DRF の外（Django 本体）で起きるエラー ------------------------------------
# JsonResponse はレンダラーを通らないので、ここだけキーをキャメルケースで書く


def _json(error, status_code):
    return JsonResponse({"errorCode": error[0], "errorMsg": error[1]}, status=status_code,
                        json_dumps_params={"ensure_ascii": False})


def csrf_failure(request, reason=""):
    """settings.CSRF_FAILURE_VIEW。Django の CSRF ミドルウェアで弾かれたとき"""
    return _json(CSRF_FAILED, status.HTTP_403_FORBIDDEN)


def not_found(request, exception=None):
    """config/urls.py の handler404（DEBUG=False のときに使われる）"""
    return _json(NOT_FOUND, status.HTTP_404_NOT_FOUND)


def server_error(request):
    """config/urls.py の handler500（DEBUG=False のときに使われる）"""
    return _json(INTERNAL_SERVER_ERROR, status.HTTP_500_INTERNAL_SERVER_ERROR)
