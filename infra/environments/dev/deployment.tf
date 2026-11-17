variable "deployment_aws_profile" {
  description = "apply 内の AWS CLI プロファイル。null は実行元の AWS 認証環境を使います。"
  type        = string
  default     = null
}
variable "migration_load_initial_data" {
  description = "dev は migrate 後にエリア・都道府県・カテゴリを投入します。既存マスターを上書きしたくない更新では false にします。"
  type        = bool
  default     = true
}
variable "migration_timeout_seconds" {
  description = "apply 内で migration の正常終了を待つ秒数。"
  type        = number
  default     = 900
}
