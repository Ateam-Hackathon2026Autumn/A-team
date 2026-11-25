output "connection" {
  description = "DB 接続情報とパスワードを格納するシークレットの ARN。パスワードの値自体は含めません。"
  value = {
    host        = aws_db_instance.main.address
    port        = aws_db_instance.main.port
    name        = aws_db_instance.main.db_name
    username    = aws_db_instance.main.username
    secret_arn  = aws_db_instance.main.master_user_secret[0].secret_arn
    resource_id = aws_db_instance.main.resource_id
  }
}

output "deletion_policy" {
  description = "実際の DB に設定する削除保護と最終スナップショット方針。"
  value = {
    deletion_protection = aws_db_instance.main.deletion_protection
    skip_final_snapshot = aws_db_instance.main.skip_final_snapshot
  }
}
