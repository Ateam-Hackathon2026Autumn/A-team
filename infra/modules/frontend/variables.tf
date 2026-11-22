variable "name" {
  description = "環境名を含む接頭辞。CloudFront の設定名に使用します。"
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,46}[a-z0-9]$", var.name))
    error_message = "name は英小文字で始まる3〜48文字の英小文字・数字・ハイフンにしてください。"
  }
}

variable "bucket_name" {
  description = "bootstrap で作成済みのフロント成果物用 S3 バケット名。環境側では参照だけ行います。"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name は3〜63文字の英小文字・数字・ハイフンにしてください。"
  }
}

variable "uploads_bucket_name" {
  description = "bootstrap のアップロード用 S3 バケット名。指定すると /images/* を配信します。"
  type        = string
  default     = null

  validation {
    condition     = var.uploads_bucket_name == null || can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.uploads_bucket_name))
    error_message = "uploads_bucket_name は3〜63文字の英小文字・数字・ハイフンにしてください。"
  }
}

variable "custom_domain" {
  description = "公開するホスト名と、既存の Route 53 パブリックホストゾーン ID。null の場合は CloudFront の標準ドメインを使います。"
  type = object({
    name    = string
    zone_id = string
  })
  default = null

  validation {
    condition = var.custom_domain == null ? true : (
      can(regex("^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?[.])+[a-z][a-z0-9-]*[a-z0-9]$", var.custom_domain.name)) &&
      can(regex("^Z[A-Z0-9]+$", var.custom_domain.zone_id))
    )
    error_message = "custom_domain には小文字の完全修飾ドメイン名と、Z で始まるホストゾーン ID を指定してください。"
  }
}

variable "api_origin" {
  description = "同じドメインの /api と /api/* を転送する ALB の接続先。null は静的配信のみ。"
  type = object({
    domain_name     = string
    protocol_policy = string
  })
  default = null

  validation {
    condition = var.api_origin == null ? true : (
      can(regex("^[A-Za-z0-9][A-Za-z0-9.-]*[A-Za-z0-9]$", var.api_origin.domain_name)) &&
      contains(["http-only", "https-only"], var.api_origin.protocol_policy)
    )
    error_message = "api_origin はスキーム・パスを含まない DNS 名と、http-only または https-only を指定してください。"
  }
}
