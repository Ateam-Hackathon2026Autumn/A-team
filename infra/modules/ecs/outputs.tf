output "cluster_name" {
  description = "ECS クラスター名。"
  value       = aws_ecs_cluster.main.name
}

output "service_name" {
  description = "バックエンドの ECS サービス名。"
  value       = aws_ecs_service.backend.name
}

output "task_definition_arn" {
  description = "デプロイと単発の DB migration に使用するタスク定義 ARN。"
  value       = aws_ecs_task_definition.backend.arn
}

output "network_configuration" {
  description = "aws ecs run-task に渡すネットワーク設定。"
  value = {
    awsvpcConfiguration = {
      subnets        = var.subnet_ids
      securityGroups = [var.security_group_id]
      assignPublicIp = "DISABLED"
    }
  }
}

output "django_secret_arn" {
  description = "Django の SECRET_KEY を格納するシークレットの ARN。値自体は出力しません。"
  value       = aws_secretsmanager_secret.django.arn
}

output "log_group_name" {
  description = "バックエンドのログを保存する CloudWatch Logs のロググループ名。"
  value       = aws_cloudwatch_log_group.backend.name
}

output "task_role_arn" {
  description = "画像用 S3 への権限を持つ、アプリ実行用 IAM ロールの ARN。"
  value       = aws_iam_role.ecs_task.arn
}

