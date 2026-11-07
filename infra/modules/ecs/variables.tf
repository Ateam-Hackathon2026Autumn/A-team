variable "name" {
  description = "環境名を含むリソース名の接頭辞（例: a-team-dev）。"
  type        = string
}

variable "subnet_ids" {
  description = "外向き通信の経路が設定済みのアプリ用 private subnet の ID 一覧。"
  type        = list(string)
}

variable "security_group_id" {
  description = "network モジュールから受け取るバックエンド用セキュリティグループの ID。"
  type        = string
}

variable "target_group_arn" {
  description = "ALB のリスナーに関連付け済みのターゲットグループ ARN。"
  type        = string
}

variable "ecr_repository" {
  description = "ECR モジュールから受け取るリポジトリ情報（URL と ARN）。"
  type = object({
    url = string
    arn = string
  })
}

variable "uploads_bucket_name" {
  description = "bootstrap で作成済みの画像・ファイル用 S3 バケット名。アプリには uploads/ と画像用 prefix の読み書きを許可します。"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.uploads_bucket_name))
    error_message = "bootstrap の uploads_bucket_name を指定してください（3〜63 文字の英小文字・数字・ハイフン）。"
  }
}

variable "image_prefixes" {
  description = "元画像・圧縮画像の prefix。アプリの環境変数と S3 アクセス権に使用します。"
  type = object({
    input  = string
    output = string
  })
  default = {
    input  = "uploads/images/"
    output = "uploads/compressed/"
  }

  validation {
    condition = alltrue([
      for prefix in [var.image_prefixes.input, var.image_prefixes.output] :
      can(regex("^[A-Za-z0-9][A-Za-z0-9/_.-]*/$", prefix)) && length(prefix) <= 512
    ])
    error_message = "画像用 prefix は英数字で始まる 512 文字以内の英数字・/・_・.・- とし、末尾を / にしてください。"
  }
}

variable "database" {
  description = "RDS モジュールから受け取る DB 接続情報と、パスワードを格納する Secrets Manager の ARN。"
  type = object({
    host       = string
    port       = number
    name       = string
    username   = string
    secret_arn = string
  })
}

variable "aws_region" {
  description = "ECS と CloudWatch Logs を配置する AWS リージョン。"
  type        = string
}

variable "aws_account_id" {
  description = "ECS タスクの IAM 信頼ポリシーで許可する AWS アカウント ID。"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
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

variable "image_tag" {
  description = "バックエンドの ECR イメージタグ（上書き不可）。desired_count を増やす前に、このタグのイメージを push します。"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid Docker image tag."
  }
}

variable "desired_count" {
  description = "ECS タスクの起動数。初回は 0 とし、イメージと Django のシークレットを登録してから 1 以上にします。"
  type        = number

  validation {
    condition     = var.desired_count >= 0 && floor(var.desired_count) == var.desired_count
    error_message = "desired_count must be a nonnegative integer."
  }
}

variable "django_allowed_hosts" {
  description = "Django が許可するホスト名の一覧。ALB のヘルスチェックはターゲットの private IP を Host にするため、dev の初期値は * です。"
  type        = list(string)
}
