output "dns_name" {
  description = "インターネット向け ALB の DNS 名。"
  value       = aws_lb.main.dns_name
}

output "target_group_arn" {
  description = "リスナーへの関連付けが完了し、ECS サービスに接続できるバックエンド用ターゲットグループの ARN。"
  value       = aws_lb_target_group.backend.arn

  # ECS rejects target groups that have not yet been associated with a listener.
  depends_on = [aws_lb_listener.http, aws_lb_listener.https]
}

output "deletion_protection" {
  description = "実際の ALB に設定する削除保護。環境全体の削除方針の確認に使用します。"
  value       = aws_lb.main.enable_deletion_protection
}
