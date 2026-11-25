variable "name" {
  description = "環境名を含むリソース名の接頭辞（例: a-team-dev）。"
  type        = string
}

variable "https_enabled" {
  description = "ALB に証明書を設定する場合、HTTPS の受信を許可します。"
  type        = bool
}

variable "aws_region" {
  description = "利用する AWS リージョン。ネットワークは AZ の a と c を使用します。"
  type        = string
}

variable "vpc_cidr" {
  description = "VPC の IPv4 /16 CIDR。/24 単位で public・アプリ・DB 用サブネットに分割します。"
  type        = string

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr)) && can(regex("/16$", var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 /16 CIDR."
  }
}

variable "single_nat_gateway" {
  description = "true では AZ a に NAT Gateway を 1 台配置します。false では AZ ごとに 1 台ずつ配置します。"
  type        = bool
}

variable "alb_ingress_cidrs" {
  description = "インターネット向け ALB へのアクセスを許可する IPv4 CIDR の一覧。"
  type        = set(string)

  validation {
    condition     = length(var.alb_ingress_cidrs) > 0 && alltrue([for cidr in var.alb_ingress_cidrs : can(cidrnetmask(cidr))])
    error_message = "Provide at least one valid IPv4 CIDR."
  }
}

variable "container_port" {
  description = "バックエンドコンテナが HTTP 接続を受け付けるポート番号。"
  type        = number

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535 && floor(var.container_port) == var.container_port
    error_message = "container_port must be an integer between 1 and 65535."
  }
}
