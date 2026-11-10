"""メールの組み立てと送信
メールの本文と認証URLを作成し、ユーザーへメールを送信するための共通処理

- 件名・本文のテンプレート。リンクは settings.FRONTEND_BASE_URL から作る
- 送信に失敗しても例外を外に出さず、ログに残す（登録などの処理自体は成功として扱う）
- 開発中は settings.EMAIL_BACKEND がコンソールなので、docker compose logs backend で本文を見られる

使う場所: notifications.py、新規登録・確認メール再送、パスワード再設定、問い合わせ受付、管理者追加
"""
import logging
from urllib.parse import quote

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)

SITE_NAME = "つながるマルシェ"


def frontend_url(path, **query):
    url = settings.FRONTEND_BASE_URL.rstrip("/") + path
    if query:
        url += "?" + "&".join(f"{k}={quote(str(v), safe='')}" for k, v in query.items())
    return url


def send(to, subject, body):
    """1通送る。失敗したら False を返してログに残す"""
    try:
        send_mail(f"【{SITE_NAME}】{subject}", body, settings.DEFAULT_FROM_EMAIL, [to])
        return True
    except Exception:
        logger.exception("メール送信に失敗しました: subject=%s", subject)
        return False


def send_email_verification(user, token):
    """メールアドレス確認のメール。リンク先はフロントの /verify-email 画面"""
    url = frontend_url("/verify-email", token=token)
    body = (
        f"{user.last_name} {user.first_name} 様\n\n"
        f"{SITE_NAME}へのご登録ありがとうございます。\n"
        "下のリンクを開いて、メールアドレスの確認を完了してください。\n\n"
        f"{url}\n\n"
        "このリンクの有効期限は24時間です。期限が切れた場合は、マイページから確認メールを再送してください。\n"
        "このメールに心当たりがない場合は、破棄してください。\n"
    )
    return send(user.email, "メールアドレスの確認", body)


def send_email_change_verification(user, token):
    """メールアドレスを変えたときの確認メール（新しいアドレスへ）"""
    url = frontend_url("/verify-email", token=token)
    body = (
        f"{user.last_name} {user.first_name} 様\n\n"
        f"{SITE_NAME}のメールアドレスを変更しました。\n"
        "下のリンクを開いて、新しいメールアドレスの確認を完了してください。\n\n"
        f"{url}\n\n"
        "このリンクの有効期限は24時間です。期限が切れた場合は、マイページから確認メールを再送してください。\n"
        "このメールに心当たりがない場合は、破棄してください。\n"
    )
    return send(user.email, "メールアドレスの確認", body)


def send_account_notice(to, name, subject, message):
    """アカウントの変更のお知らせ（メールアドレス変更・パスワード変更・退会）。本人が操作していないときに気づけるように送る"""
    body = (
        f"{name} 様\n\n{message}\n\n"
        "この操作に心当たりがない場合は、お問い合わせフォームからすぐにご連絡ください。\n"
    )
    return send(to, subject, body)
