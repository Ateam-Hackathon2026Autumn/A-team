variable "name" {
  description = "環境名を含むリソース名の接頭辞（例: a-team-dev）。"
  type        = string
}

variable "vpc_id" {
  description = "バックエンドのターゲットを配置する VPC の ID。"
  type        = string
}

variable "subnet_ids" {
  description = "ALB を配置する public subnet の ID 一覧。2 つ以上の AZ を指定します。"
  type        = list(string)
}

variable "security_group_id" {
  description = "network モジュールから受け取る ALB 用セキュリティグループの ID。"
  type        = string
}

variable "certificate_arn" {
  description = "同一リージョンの ACM 証明書 ARN（任意）。指定すると HTTPS と HTTP から HTTPS へのリダイレクトを有効にします。"
  type        = string

  validation {
    condition     = var.certificate_arn == null ? true : can(regex("^arn:aws:acm:", var.certificate_arn))
    error_message = "certificate_arn must be null or an ACM certificate ARN."
  }
}

variable "deletion_protection" {
  description = "ALB の削除保護。削除する前に false に変更して apply します。"
  type        = bool
}

variable "container_port" {
  description = "バックエンドコンテナが HTTP 接続を受け付けるポート番号。"
  type        = number

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535 && floor(var.container_port) == var.container_port
    error_message = "container_port must be an integer between 1 and 65535."
  }
}
