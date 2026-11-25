variable "path_prefix" {
  description = "非機密のアプリ設定を保存する Parameter Store の階層（例: /a-team/dev）。末尾の / は付けません。"
  type        = string

  validation {
    condition     = can(regex("^/[A-Za-z0-9_.-]+(/[A-Za-z0-9_.-]+)*$", var.path_prefix))
    error_message = "path_prefix は / で始め、末尾や途中に空の階層を含めないでください。"
  }
}

variable "uploads_bucket_name" {
  description = "ユーザー画像の保存先。フロント成果物用バケットとは別です。"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.uploads_bucket_name))
    error_message = "uploads_bucket_name は3〜63文字の英小文字・数字・ハイフンにしてください。"
  }
}

variable "frontend_url" {
  description = "CloudFront の HTTPS 公開 origin。CSRF の比較に使うためパス・末尾の / は含めません。"
  type        = string

  validation {
    condition     = can(regex("^https://[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$", var.frontend_url))
    error_message = "frontend_url は https:// で始まる origin を指定し、パス・末尾の / は付けないでください。"
  }
}
