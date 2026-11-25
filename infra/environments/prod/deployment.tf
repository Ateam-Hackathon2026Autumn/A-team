variable "deployment_aws_profile" {
  description = "apply 内の AWS CLI プロファイル。null は実行元の AWS 認証環境を使います。"
  type        = string
  default     = null
}
variable "migration_load_initial_data" {
  description = "migrate 後に初期マスターを投入する場合のみ true。通常のリリースは false。"
  type        = bool
  default     = false
}
variable "migration_timeout_seconds" {
  description = "apply 内で migration の正常終了を待つ秒数。"
  type        = number
  default     = 900
}
