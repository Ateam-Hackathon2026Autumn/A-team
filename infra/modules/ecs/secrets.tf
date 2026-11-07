# Register the secret value out of band after the first apply. Terraform manages
# only the container so DJANGO_SECRET_KEY is absent from configuration and state.
resource "aws_secretsmanager_secret" "django" {
  name                    = "${var.name}/django-secret-key"
  description             = "Django の SECRET_KEY。JSON ではなく単一の文字列として保存します。"
  recovery_window_in_days = 7
}
