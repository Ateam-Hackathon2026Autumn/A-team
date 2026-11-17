locals {
  # このモジュールは公開 URL・バケット名など、秘密ではない設定だけを管理する。
  # DB_PASSWORD・DJANGO_SECRET_KEY 等の秘密値は Secrets Manager の既存経路を使う。
  parameter_values = {
    AWS_STORAGE_BUCKET_NAME     = var.uploads_bucket_name
    FRONTEND_BASE_URL           = var.frontend_url
    DJANGO_CSRF_TRUSTED_ORIGINS = var.frontend_url
    DJANGO_COOKIE_SECURE        = "true"
  }

  parameter_suffixes = {
    AWS_STORAGE_BUCKET_NAME     = "uploads-bucket-name"
    FRONTEND_BASE_URL           = "frontend-base-url"
    DJANGO_CSRF_TRUSTED_ORIGINS = "csrf-trusted-origins"
    DJANGO_COOKIE_SECURE        = "django-cookie-secure"
  }
}

resource "aws_ssm_parameter" "application" {
  for_each = local.parameter_suffixes

  name        = "${var.path_prefix}/${each.value}"
  description = "Application configuration for ${each.key}"
  type        = "String"
  tier        = "Standard"
  value       = local.parameter_values[each.key]
}
