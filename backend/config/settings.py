import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-secret-key")
DEBUG = os.getenv("DJANGO_DEBUG", "true").lower() in {"1", "true", "yes", "on"}
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend"
    ).split(",")
    if host.strip()
]

# フロント（Vite: localhost:5173）は /api をプロキシで backend に転送するため、
# ブラウザが送る Origin（http://localhost:5173）を信頼する。これがないと POST が CSRF で 403 になる
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
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
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
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
        "NAME": os.getenv("DB_NAME", "hackathon"),
        "USER": os.getenv("DB_USER", "hackathon"),
        "PASSWORD": os.getenv("DB_PASSWORD", "hackathon_password"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "3306"),
        "OPTIONS": {"charset": "utf8mb4"},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# 画像・書類、アップロードしたファイルの保存先を S3 にする設定
STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
# 保存先の S3 バケット名。"..." は仮の値なので、実際に作ったバケット名を環境変数で渡す
AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME", "...")
AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ap-northeast-1")

# 公開用の画像（商品・農園・体験など）は署名なしのURLで返す。
# 申請書類・チャット添付など非公開のファイルは、表示のたびに期限付きURLを個別に発行する（api-spec「ファイル」）
AWS_QUERYSTRING_AUTH = False
# 非公開ファイル（申請書類・チャット添付）の期限付きURLの有効期間（秒）→ api/services/storage.py
PRIVATE_FILE_URL_EXPIRE = 60 * 5

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    # rating_avg などの DECIMAL を文字列ではなく数値で返す
    "COERCE_DECIMAL_TO_STRING": False,
    # 共通エラー形式。api/common/exceptions.py を実装したらコメントを外す
    # "EXCEPTION_HANDLER": "api.common.exceptions.exception_handler",
    # 同じIPから1時間5回まで（api/common/throttles.py で scope を指定して使う）
    "DEFAULT_THROTTLE_RATES": {
        "inquiry": "5/hour",
        "password_reset": "5/hour",
    },
}

# --- 認証・セッション -------------------------------------------------------
# フロントは csrftoken Cookie を読んで X-CSRFToken ヘッダーに載せるので HttpOnly にしない（Django の初期値のまま）
CSRF_COOKIE_HTTPONLY = False
# パスワード再設定リンクの有効期限（秒）。管理者の初回パスワード設定にも使う
PASSWORD_RESET_TIMEOUT = 60 * 60

# --- メール -------------------------------------------------------------------
# 開発中はメールを送らずコンソール（docker compose logs backend）に出す
EMAIL_BACKEND = os.getenv("DJANGO_EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = os.getenv("DJANGO_DEFAULT_FROM_EMAIL", "no-reply@example.com")
# メール本文のリンク（パスワード再設定・ゲストの注文確認など）に使うフロントのURL
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

# --- Stripe -------------------------------------------------------------------
# api/services/payments.py で使う。キーはコミットせず環境変数で渡す
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

LANGUAGE_CODE = "ja"
TIME_ZONE = "Asia/Tokyo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
