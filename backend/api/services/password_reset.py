"""パスワード再設定のリンク（uid・token）の作成と確認

Django の PasswordResetTokenGenerator を使う。トークンは DB に保存しない。
- 有効期限は settings.PASSWORD_RESET_TIMEOUT（1時間）
- トークンにはパスワードのハッシュ・最後のログイン日時・メールアドレスが含まれるので、
  パスワードを変えた（＝一度使った）・ログインした・メールアドレスを変えたら使えなくなる
- 利用停止中・退会済み（is_active=False か deleted_at あり）の人には使えない
- uid はユーザーIDを base64 にしたもの（Django の標準のやり方）

使う場所: POST /auth/password-reset、POST /auth/password-reset/confirm、
          運営スタッフの追加（初回のパスワード設定に同じリンクを使う。make_url）
"""
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from marche.models import User

from .mail import frontend_url

CONFIRM_PATH = "/password-reset/confirm"


def active_users():
    return User.objects.filter(is_active=True, deleted_at__isnull=True)


def make_url(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return frontend_url(CONFIRM_PATH, uid=uid, token=default_token_generator.make_token(user))


def find_user(uid, token, lock=False):
    """uid・token が正しければユーザーを返す（lock=True なら行をロックして読む）。だめなら None"""
    try:
        pk = int(force_str(urlsafe_base64_decode(uid)))
    except (TypeError, ValueError, OverflowError, UnicodeDecodeError):
        return None
    if not 1 <= pk <= 2 ** 63 - 1:
        return None
    users = active_users().select_for_update() if lock else active_users()
    user = users.filter(pk=pk).first()
    if user is None or not default_token_generator.check_token(user, token):
        return None
    return user
