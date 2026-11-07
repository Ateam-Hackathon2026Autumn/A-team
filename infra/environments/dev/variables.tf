variable "aws_region" {
  description = "利用する AWS リージョン。ネットワークは AZ の a と c を使用します。"
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_account_id" {
  description = "対象の AWS アカウント ID。backend.s3.tfbackend の allowed_account_ids と一致させます。"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "project_name" {
  description = "リソース名に付ける短い接頭辞。先頭は英小文字にします。"
  type        = string
  default     = "a-team"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,14}[a-z0-9]$", var.project_name))
    error_message = "Use 3-16 lowercase letters, digits or hyphens; start with a letter and end with a letter or digit."
  }
}

variable "uploads_bucket_name" {
  description = "bootstrap の uploads_bucket_name 出力。画像用 S3 を再作成せず、ECS の task role に uploads/ と画像用 prefix のアクセス権を付与します。"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.uploads_bucket_name))
    error_message = "bootstrap で作成済みの画像・ファイル用バケット名を指定してください。"
  }
}

variable "vpc_cidr" {
  description = "VPC の IPv4 /16 CIDR。/24 単位で public・アプリ・DB 用サブネットに分割します。"
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrnetmask(var.vpc_cidr)) && can(regex("/16$", var.vpc_cidr))
    error_message = "vpc_cidr must be a valid IPv4 /16 CIDR."
  }
}

variable "single_nat_gateway" {
  description = "true では AZ a に NAT Gateway を 1 台配置します。false では AZ ごとに 1 台ずつ配置します。"
  type        = bool
  default     = true
}

variable "alb_ingress_cidrs" {
  description = "インターネット向け ALB へのアクセスを許可する IPv4 CIDR の一覧。"
  type        = set(string)
  default     = ["0.0.0.0/0"]

  validation {
    condition     = length(var.alb_ingress_cidrs) > 0 && alltrue([for cidr in var.alb_ingress_cidrs : can(cidrnetmask(cidr))])
    error_message = "Provide at least one valid IPv4 CIDR."
  }
}

variable "certificate_arn" {
  description = "同一リージョンの ACM 証明書 ARN（任意）。指定すると HTTPS と HTTP から HTTPS へのリダイレクトを有効にします。"
  type        = string
  default     = null

  validation {
    condition     = var.certificate_arn == null ? true : can(regex("^arn:aws:acm:", var.certificate_arn))
    error_message = "certificate_arn must be null or an ACM certificate ARN."
  }
}

variable "deletion_protection" {
  description = "ALB と RDS の削除保護。dev を削除する前に false に変更して apply します。"
  type        = bool
  default     = true
}

variable "container_port" {
  description = "バックエンドコンテナが HTTP 接続を受け付けるポート番号。"
  type        = number
  default     = 8000

  validation {
    condition     = var.container_port >= 1 && var.container_port <= 65535 && floor(var.container_port) == var.container_port
    error_message = "container_port must be an integer between 1 and 65535."
  }
}

variable "image_tag" {
  description = "バックエンドの ECR イメージタグ（上書き不可）。desired_count を増やす前に、このタグのイメージを push します。"
  type        = string
  default     = "initial"

  validation {
    condition     = can(regex("^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$", var.image_tag))
    error_message = "image_tag must be a valid Docker image tag."
  }
}

variable "desired_count" {
  description = "ECS タスクの起動数。初回は 0 とし、イメージと Django のシークレットを登録してから 1 以上にします。"
  type        = number
  default     = 0

  validation {
    condition     = var.desired_count >= 0 && floor(var.desired_count) == var.desired_count
    error_message = "desired_count must be a nonnegative integer."
  }
}

variable "django_allowed_hosts" {
  description = "Django が許可するホスト名の一覧。ALB のヘルスチェックはターゲットの private IP を Host にするため、dev の初期値は * です。"
  type        = list(string)
  default     = ["*"]
}

variable "db_name" {
  description = "RDS 作成時に用意する MySQL データベース名。"
  type        = string
  default     = "hackathon"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9]{0,63}$", var.db_name))
    error_message = "db_name must start with a letter and contain up to 64 alphanumeric characters."
  }
}

variable "db_username" {
  description = "RDS のマスターユーザー名。現在の dev 構成ではバックエンドからの接続にも使用します。"
  type        = string
  default     = "appadmin"
}

variable "db_engine_version" {
  description = "RDS MySQL のバージョン。8.4 を指定すると、対応するマイナーバージョンを AWS が選択します。"
  type        = string
  default     = "8.4"
}

variable "db_instance_class" {
  description = "RDS のインスタンスクラス（例: db.t4g.micro）。"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_multi_az" {
  description = "true にすると、別の AZ に RDS のスタンバイを配置して Multi-AZ を有効にします。"
  type        = bool
  default     = false
}

variable "db_skip_final_snapshot" {
  description = "DB 削除時に最終スナップショットを作成する場合は false にします。"
  type        = bool
  default     = false
}

variable "db_final_snapshot_identifier" {
  description = "最終スナップショットの一意な名前。スナップショットの作成をスキップしない場合に必須です。"
  type        = string
  default     = null

  validation {
    condition = var.db_final_snapshot_identifier == null ? true : (
      can(regex("^[a-zA-Z][a-zA-Z0-9-]{0,253}[a-zA-Z0-9]$", var.db_final_snapshot_identifier)) &&
      !strcontains(var.db_final_snapshot_identifier, "--")
    )
    error_message = "Use 2-255 letters, digits and hyphens, starting with a letter, with no trailing or repeated hyphens."
  }
}
