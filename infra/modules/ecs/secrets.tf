# Terraform は入れ物のみ管理し、サービス起動前にスクリプトが未登録の値を生成する。
# 秘密値そのものは Terraform の引数・state・output へ渡さない。
resource "aws_secretsmanager_secret" "django" {
  name                    = "${var.name}/django-secret-key"
  description             = "Django の SECRET_KEY。JSON ではなく単一の文字列として保存します。"
  recovery_window_in_days = var.django_secret_recovery_window_in_days
}
