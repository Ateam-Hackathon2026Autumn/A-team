import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def env(name, default=""):
    """環境変数を読む。空文字（compose.yaml の ${VAR:-} など）は「設定なし」として既定値にする"""
    value = os.getenv(name, "").strip()
    return value or default


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-secret-key")
DEBUG = env("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes", "on"}

# 本番（DJANGO_DEBUG=false）なのに、開発用や短すぎる SECRET_KEY のままなら起動しない。
# ローカルは compose.yaml で DJANGO_DEBUG=true を渡すので、このチェックは働かない
DEV_SECRET_KEYS = {"dev-only-secret-key", "hackathon_secret_key"}
if not DEBUG and (SECRET_KEY in DEV_SECRET_KEYS or len(SECRET_KEY) < 32):
    raise ImproperlyConfigured(
        "DJANGO_DEBUG=false のときは、本番用の DJANGO_SECRET_KEY（32文字以上のランダムな文字列）を設定してください。")
ALLOWED_HOSTS = [
    host.strip()
    for host in env(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend"
    ).split(",")
    if host.strip()
]

# フロント（Vite: localhost:5173）は /api をプロキシで backend に転送するため、
# ブラウザが送る Origin（http://localhost:5173）を信頼する。これがないと POST が CSRF で 403 になる
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in env(
        "DJANGO_CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "storages",
    "marche",  # モデル・マイグレーション・バッチ（管理コマンド）
    "api",  # API の views / serializers / services / tests
]

AUTH_USER_MODEL = "marche.User"

MIDDLEWARE = [
    # ALB のヘルスチェック（/api/health/）は ALLOWED_HOSTS の確認より前に 200 を返す（api/common/middleware.py）
    "api.common.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # クエリパラメーターのキャメルケース（?categoryId=1）をスネークケースに変換する
    "djangorestframework_camel_case.middleware.CamelCaseMiddleWare",
    # /api/ のレスポンスに Cache-Control: no-store を付ける
    "api.common.middleware.NoStoreMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", "hackathon"),
        "USER": env("DB_USER", "hackathon"),
        "PASSWORD": env("DB_PASSWORD", "hackathon_password"),
        "HOST": env("DB_HOST", "127.0.0.1"),
        "PORT": env("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

# パスワード規則（Notion の新規登録APIの定義：英大文字・英小文字・数字・記号をそれぞれ1文字以上含む8〜30文字）に加えて、
# 流出パスワードの一覧と、姓・名・メールアドレスに似たパスワードも弾く（理由は 400 の details.password で返す）
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "api.common.validators.PasswordPolicyValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
]

# 画像・書類、アップロードしたファイルの保存先
# - 本番：S3。バケット名を環境変数 AWS_STORAGE_BUCKET_NAME で渡す
# - 開発：バケット名を渡さなければ、backend/media/ に保存する（AWS の設定がなくても画像を登録できる）。
#   表示用のURLは MEDIA_URL から作り、DEBUG のときだけ Django が /media/ を返す（config/urls.py）
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", "")
USE_S3 = bool(AWS_STORAGE_BUCKET_NAME)
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage" if USE_S3 else "django.core.files.storage.FileSystemStorage"
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
MEDIA_ROOT = BASE_DIR / "media"
# ブラウザは frontend（localhost:5173）を開いているので、画像は backend（localhost:8000）のURLで返す
MEDIA_URL = env("DJANGO_MEDIA_URL", "http://localhost:8000/media/")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", "ap-northeast-1")
# CloudFront から画像を配信するときのドメイン（例: d123.cloudfront.net）。空なら S3 の URL を返す
AWS_S3_CUSTOM_DOMAIN = env("AWS_S3_CUSTOM_DOMAIN") or None
PUBLIC_IMAGE_BASE_URL = env("DJANGO_PUBLIC_IMAGE_BASE_URL").rstrip("/")

# 公開画像は CloudFront のURLで返す（api/common/images.py）。
# 申請書類・チャット添付など非公開のファイルは、表示のたびに期限付きURLを個別に発行する（api-spec「ファイル」）
AWS_QUERYSTRING_AUTH = False
# 非公開ファイル（申請書類・チャット添付）の期限付きURLの有効期間（秒）→ api/services/storage.py
PRIVATE_FILE_URL_EXPIRE = 60 * 5


# djangorestframework-camel-case: リクエストの addressLine1 を address_line1 に直す（初期設定では address_line_1 になり、
# レスポンスの camelize（address_line1 → addressLine1）と往復しないため）
JSON_CAMEL_CASE = {
    "JSON_UNDERSCOREIZE": {"no_underscore_before_number": True},
}

REST_FRAMEWORK = {
    # 未ログインにも CSRF を確認し、未ログインは 401 にするセッション認証
    "DEFAULT_AUTHENTICATION_CLASSES": ["api.common.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # JSON のキーは、フロントとはキャメルケース（lastName）、Python 側はスネークケース（last_name）
    "DEFAULT_RENDERER_CLASSES": ["djangorestframework_camel_case.render.CamelCaseJSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "djangorestframework_camel_case.parser.CamelCaseJSONParser",
        "djangorestframework_camel_case.parser.CamelCaseMultiPartParser",
        "djangorestframework_camel_case.parser.CamelCaseFormParser",
    ],
    # rating_avg などの DECIMAL を文字列ではなく数値で返す
    "COERCE_DECIMAL_TO_STRING": False,
    # 共通エラー形式 {errorCode, errorMsg, details}
    "EXCEPTION_HANDLER": "api.common.exceptions.exception_handler",
    # 同じIPからの回数制限（api/common/throttles.py の IPRateThrottle で scope を指定して使う）
    "DEFAULT_THROTTLE_RATES": {
        "signin": "20/hour",
        "signup": "10/hour",
        "email_verification_resend": "10/hour",
        "inquiry": "5/hour",
        "password_reset": "5/hour",
        "password_reset_confirm": "20/hour",
        "report": "10/hour",
        "order": "30/hour",
        "password_check": "10/hour",
        "email_verification_resend": "10/hour",
        "email_verification_resend_minute": "1/min",
        "email_verification_resend_hour": "5/hour",
        # 画像アップロード（同じユーザー。api/views/public/uploads.py）
        "image_upload": "60/hour",
    },
}

# --- 認証・セッション -------------------------------------------------------
# フロントは csrftoken Cookie を読んで X-CSRFToken ヘッダーに載せるので HttpOnly にしない（Django の初期値のまま）
CSRF_COOKIE_HTTPONLY = False
# Django の CSRF ミドルウェアで弾かれたときも共通エラー形式（CSRF_FAILED）で返す
CSRF_FAILURE_VIEW = "api.common.exceptions.csrf_failure"
# セッションは登録・ログインから14日間の固定期限（アクセスしても延長しない）
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
# Secure 属性は本番（https）だけ有効にする。http のローカル環境では Cookie が保存されないことがあるため
COOKIE_SECURE = env("DJANGO_COOKIE_SECURE", "false").lower() in {"1", "true", "yes", "on"}
SESSION_COOKIE_SECURE = COOKIE_SECURE
CSRF_COOKIE_SECURE = COOKIE_SECURE
# メール認証リンクの有効期限（秒）
EMAIL_VERIFICATION_TIMEOUT = 60 * 60 * 24
# パスワード再設定リンクの有効期限（秒）。管理者の初回パスワード設定にも使う
PASSWORD_RESET_TIMEOUT = 60 * 60

# --- 規約 ---------------------------------------------------------------------
# 現行の版。新規登録で送られた版と違えば 409 POLICY_VERSION_MISMATCH。フロントの表示と合わせて更新する
TERMS_VERSION = env("TERMS_VERSION", "2026-10-01")
PRIVACY_POLICY_VERSION = env("PRIVACY_POLICY_VERSION", "2026-10-01")

# --- メール -------------------------------------------------------------------
# 開発中はメールを送らずコンソール（docker compose logs backend）に出す
EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL", "no-reply@example.com")
# メール本文のリンク（パスワード再設定・ゲストの注文確認など）に使うフロントのURL
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", "http://localhost:5173")

# --- Stripe -------------------------------------------------------------------
# api/services/payments.py で使う。キーはコミットせず環境変数で渡す
STRIPE_SECRET_KEY = env("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = env("STRIPE_WEBHOOK_SECRET", "")

# --- 本番（AWS）-----------------------------------------------------------------
# ALB で HTTPS を外して http で受けるので、ALB が付ける X-Forwarded-Proto で HTTPS かどうかを判定する。
# ローカル（DEBUG）では使わない
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# --- ログ ---------------------------------------------------------------------
# すべて標準出力に出す（docker compose logs・CloudWatch Logs で見る）。
# Django の既定では DEBUG=false のとき 500 エラーの詳細がどこにも出ないので、django.request の ERROR も出す
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        # runserver のアクセスログ・SQL などは今までどおり（Django の既定）にする
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.request": {"handlers": ["console"], "level": "ERROR", "propagate": False},
        "django.server": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
