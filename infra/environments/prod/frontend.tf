# CloudFront・OAC・配信許可は prod、S3 本体と成果物は bootstrap で保持する。
# アプリ更新時は差分更新。ビルド成果物の配置は別のデプロイ手順で行う。
module "frontend" {
  source = "../../modules/frontend"

  name        = local.name
  bucket_name = "${local.name}-frontend-${var.aws_account_id}-${var.aws_region}"
  api_origin = {
    domain_name     = var.backend_origin_domain_name != null ? var.backend_origin_domain_name : module.alb.dns_name
    protocol_policy = var.certificate_arn == null ? "http-only" : "https-only"
  }
}

variable "backend_origin_domain_name" {
  description = "CloudFront→ALB を HTTPS にする場合の、ALB 証明書に一致する接続先 DNS 名。HTTP の仮構成では null で ALB の DNS 名を使います。"
  type        = string
  default     = null

  validation {
    condition     = var.backend_origin_domain_name == null ? true : can(regex("^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$", var.backend_origin_domain_name))
    error_message = "backend_origin_domain_name はスキーム・パスを含まない DNS 名にしてください。"
  }

  validation {
    condition     = var.certificate_arn == null || var.backend_origin_domain_name != null
    error_message = "ALB の HTTPS を有効にする場合は、証明書に一致して ALB を指す backend_origin_domain_name も指定してください。"
  }
}
