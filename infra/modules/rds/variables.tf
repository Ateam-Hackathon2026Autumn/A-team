variable "name" {
  description = "環境名を含むリソース名の接頭辞（例: a-team-dev）。"
  type        = string
}

variable "subnet_ids" {
  description = "外向きルートを持たない DB 用サブネット。2 つ以上の AZ に配置します。"
  type        = list(string)
}

variable "security_group_id" {
  description = "network モジュールから受け取る DB 用セキュリティグループの ID。"
  type        = string
}

variable "db_name" {
  description = "RDS 作成時に用意する MySQL データベース名。"
  type        = string

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9]{0,63}$", var.db_name))
    error_message = "db_name must start with a letter and contain up to 64 alphanumeric characters."
  }
}

variable "db_username" {
  description = "RDS のマスターユーザー名。現在の dev 構成ではバックエンドからの接続にも使用します。"
  type        = string
}

variable "db_engine_version" {
  description = "RDS MySQL のバージョン。8.4 を指定すると、対応するマイナーバージョンを AWS が選択します。"
  type        = string
}

variable "db_instance_class" {
  description = "RDS のインスタンスクラス（例: db.t4g.micro）。"
  type        = string
}

variable "db_multi_az" {
  description = "true にすると、別の AZ に RDS のスタンバイを配置して Multi-AZ を有効にします。"
  type        = bool
}

variable "db_skip_final_snapshot" {
  description = "DB 削除時に最終スナップショットを作成する場合は false にします。"
  type        = bool
}

variable "db_final_snapshot_identifier" {
  description = "最終スナップショットの一意な名前。スナップショットの作成をスキップしない場合に必須です。"
  type        = string

  validation {
    condition = var.db_final_snapshot_identifier == null ? true : (
      can(regex("^[a-zA-Z][a-zA-Z0-9-]{0,253}[a-zA-Z0-9]$", var.db_final_snapshot_identifier)) &&
      !strcontains(var.db_final_snapshot_identifier, "--")
    )
    error_message = "Use 2-255 letters, digits and hyphens, starting with a letter, with no trailing or repeated hyphens."
  }
}

variable "deletion_protection" {
  description = "RDS の削除保護。削除する前に false に変更して apply します。"
  type        = bool
}
