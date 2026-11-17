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
