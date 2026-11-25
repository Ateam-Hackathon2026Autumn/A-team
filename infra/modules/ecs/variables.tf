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
    host        = string
    port        = number
    name        = string
    username    = string
    secret_arn  = string
    resource_id = string
  })
}

variable "image_digest" {
  description = "push 済み ECR イメージの digest。指定時はタグでなく digest に固定します。"
  type        = string
  default     = null

  validation {
    condition     = var.image_digest == null ? true : can(regex("^sha256:[a-f0-9]{64}$", var.image_digest))
    error_message = "image_digest は sha256: と64文字の小文字16進数で指定してください。"
  }
}

variable "deployment_aws_profile" {
  description = "apply 内の AWS CLI に渡すプロファイル。null は apply 元の AWS 認証環境を引き継ぎます。"
  type        = string
  default     = null
}

variable "migration_load_initial_data" {
  description = "migrate 成功後に初期マスターを投入します。通常のリリースは false にします。"
  type        = bool
  default     = false
}

variable "migration_load_dev_seed" {
  description = "dev 環境で migrate 成功後に seed_dev を実行します。"
  type        = bool
  default     = false
}

variable "migration_timeout_seconds" {
  description = "単発 migration の完了待ち秒数。"
  type        = number
  default     = 900

  validation {
    condition     = var.migration_timeout_seconds > 0 && floor(var.migration_timeout_seconds) == var.migration_timeout_seconds
    error_message = "migration_timeout_seconds は正の整数にしてください。"
  }
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
  description = "バックエンドの ECR イメージタグ。環境の plan / apply より先に bootstrap 管理の ECR へ push し、通常は解決済みの image_digest で起動します。"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid Docker image tag."
  }
}

variable "desired_count" {
  description = "ECS タスクの起動数。1以上では apply 内の Secret 準備・migration 成功後に起動します。0 は基盤準備・停止用です。"
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

variable "application_parameter_arns" {
  description = "Parameter Store モジュールの output。ECS 起動時に、同名の環境変数として注入します。"
  type = object({
    AWS_STORAGE_BUCKET_NAME      = string
    FRONTEND_BASE_URL            = string
    DJANGO_PUBLIC_IMAGE_BASE_URL = string
    DJANGO_CSRF_TRUSTED_ORIGINS  = string
    DJANGO_COOKIE_SECURE         = string
  })

  validation {
    condition = alltrue([
      for arn in values(var.application_parameter_arns) :
      startswith(arn, "arn:aws:ssm:${var.aws_region}:${var.aws_account_id}:parameter/")
    ])
    error_message = "application_parameter_arns は、同じアカウント・リージョンの SSM パラメータ ARN を指定してください。"
  }
}

variable "application_config_revision" {
  description = "設定モジュールが出力する非機密設定の SHA-256。変更時に実行中のタスクを入れ替えます。"
  type        = string

  validation {
    condition     = can(regex("^[a-f0-9]{64}$", var.application_config_revision))
    error_message = "application_config_revision は設定値から計算した SHA-256 を指定してください。"
  }
}

variable "django_secret_recovery_window_in_days" {
  description = "Django Secret 削除時の復旧期間。0 は復旧なしの削除、7〜30 は復旧可能な日数です。dev だけ0を使用します。"
  type        = number
  default     = 7

  validation {
    condition = (
      var.django_secret_recovery_window_in_days == 0 ||
      (var.django_secret_recovery_window_in_days >= 7 &&
        var.django_secret_recovery_window_in_days <= 30 &&
      floor(var.django_secret_recovery_window_in_days) == var.django_secret_recovery_window_in_days)
    )
    error_message = "django_secret_recovery_window_in_days は0、または7〜30の整数にしてください。"
  }
}
