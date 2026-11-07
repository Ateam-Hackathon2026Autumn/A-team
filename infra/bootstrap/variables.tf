variable "aws_region" {
  description = "state 用と画像・ファイル用の S3 バケットを作成する AWS リージョン。"
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_account_id" {
  description = "対象の AWS アカウント ID。誤ったアカウントへの apply を防ぎます。"
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must contain exactly 12 digits."
  }
}

variable "project_name" {
  description = "リソースの Project タグに設定するプロジェクト名。"
  type        = string
  default     = "a-team"
}

variable "state_bucket_name" {
  description = "Terraform state 専用の、グローバルに一意な S3 バケット名。"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.state_bucket_name))
    error_message = "Use 3-63 lowercase letters, digits or hyphens, starting and ending with a letter or digit."
  }
}

variable "uploads_bucket_name" {
  description = "画像・その他ファイル用の、グローバルに一意な S3 バケット名。state 用とは別の名前を指定します。"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.uploads_bucket_name))
    error_message = "バケット名は 3〜63 文字の英小文字・数字・ハイフンとし、先頭と末尾は英数字にしてください。"
  }

  validation {
    condition     = var.uploads_bucket_name != var.state_bucket_name
    error_message = "画像・ファイル用バケットは、state 用バケットとは異なる名前にしてください。"
  }
}
