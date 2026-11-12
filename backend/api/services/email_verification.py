"""メールアドレスの確認（メール認証）
新規会員登録時に送信するメール認証用のトークンを生成し、ユーザーがメール内の認証リンクを開いた際に、メールアドレスを確認済みにする処理

トークンは DB に保存しない署名付きトークン（django.core.signing）。中身は user_id とメールアドレス。
- 有効期限は settings.EMAIL_VERIFICATION_TIMEOUT（24時間）
- 確認済みになったら使えない（email_verified_at が空のときだけ更新する）
- メールアドレスを変えたら、古いアドレス宛てのトークンは使えない
- 再送しても古いトークンは期限内なら有効のまま（ステップ1で決定）

使う場所: POST /users（新規登録）、POST /auth/email-verification/resend、POST /auth/email-verification/confirm
"""
from django.conf import settings
from django.core import signing
from django.utils import timezone

from marche.models import User

SALT = "marche.email-verification"


def make_token(user):
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=SALT, compress=True)


def verify(token):
    """トークンを確かめてメールアドレスを確認済みにする。

    成功したらそのユーザーを返す。無効・期限切れ・使用済み・メールアドレス不一致なら None。
    同時に2回呼ばれても、確認済みにできるのは1回だけ。
    """
    try:
        payload = signing.loads(token, salt=SALT, max_age=settings.EMAIL_VERIFICATION_TIMEOUT)
    except signing.BadSignature:  # 期限切れ（SignatureExpired）もここに含まれる
        return None

    # 署名が正しければ make_token() が作った形のはずだが、念のため形も確かめる
    if not isinstance(payload, dict):
        return None
    uid, email = payload.get("uid"), payload.get("email")
    if not isinstance(uid, int) or isinstance(uid, bool) or not isinstance(email, str):
        return None

    updated = User.objects.filter(
        pk=uid,
        email=email,
        is_active=True,
        email_verified_at__isnull=True,
    ).update(email_verified_at=timezone.now())
    if updated != 1:
        return None
    return User.objects.get(pk=uid)
