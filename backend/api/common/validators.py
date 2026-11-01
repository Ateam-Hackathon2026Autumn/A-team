"""入力値の共通ルール"""
import re

from django.core.exceptions import ValidationError

# 半角英大文字・半角英小文字・数字・半角記号をそれぞれ1文字以上含む8〜30文字。空白・全角文字は不可
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*[0-9])(?=.*[!-/:-@\[-`{-~])[\x21-\x7E]{8,30}$")


class PasswordPolicyValidator:
    """settings.AUTH_PASSWORD_VALIDATORS に登録するパスワード規則（Notion の新規登録APIの定義）"""

    message = "パスワードは半角の英大文字・英小文字・数字・記号をそれぞれ1文字以上含む8〜30文字で入力してください。"

    def validate(self, password, user=None):
        if not PASSWORD_PATTERN.match(password or ""):
            raise ValidationError(self.message, code="password_policy")

    def get_help_text(self):
        return self.message
