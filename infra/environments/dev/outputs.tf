output "vpc_id" {
  description = "アプリ用 VPC の ID。"
  value       = module.network.vpc_id
}

output "alb_dns_name" {
  description = "ALB の DNS 名。HTTPS 接続時は証明書に対応するカスタムドメインを使用します。"
  value       = module.alb.dns_name
}

output "ecr_repository_url" {
  description = "バックエンドのコンテナイメージを push する ECR リポジトリの URL。"
  value       = module.ecr.repository.url
}

output "ecs_cluster_name" {
  description = "デプロイと単発の DB migration タスクに使用する ECS クラスター名。"
  value       = module.ecs.cluster_name
}

output "ecs_service_name" {
  description = "バックエンドの ECS サービス名。"
  value       = module.ecs.service_name
}

output "ecs_task_definition_arn" {
  description = "バックエンドのタスク定義 ARN。単発の DB migration にも使用します。"
  value       = module.ecs.task_definition_arn
}

output "ecs_network_configuration" {
  description = "aws ecs run-task の --network-configuration に渡すネットワーク設定。"
  value       = module.ecs.network_configuration
}

output "rds_address" {
  description = "VPC 内から接続する MySQL のプライベートエンドポイント。"
  value       = module.rds.connection.host
}

output "rds_master_secret_arn" {
  description = "AWS が管理する RDS マスターパスワードのシークレット ARN。値自体は出力しません。"
  value       = module.rds.connection.secret_arn
}

output "django_secret_arn" {
  description = "タスク起動前に Django の SECRET_KEY を単一の文字列として登録するシークレットの ARN。"
  value       = module.ecs.django_secret_arn
}

output "backend_log_group_name" {
  description = "バックエンドタスクのログを保存する CloudWatch Logs のロググループ名。"
  value       = module.ecs.log_group_name
}

output "ecs_task_role_arn" {
  description = "アプリが画像用 S3 を利用する IAM ロール。IAM ポリシーの検証にも使用します。"
  value       = module.ecs.task_role_arn
}

