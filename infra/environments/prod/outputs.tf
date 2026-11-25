output "vpc_id" {
  description = "アプリ用 VPC の ID。"
  value       = module.network.vpc_id
}

output "alb_dns_name" {
  description = "ALB の DNS 名。HTTPS 接続時は証明書に対応するカスタムドメインを使用します。"
  value       = module.alb.dns_name
}

output "frontend_bucket_name" {
  description = "フロント成果物の常駐 S3 バケット名。bootstrap で管理します。"
  value       = module.frontend.bucket_name
}

output "frontend_url" {
  description = "画面と /api/* の共通入口になる CloudFront HTTPS URL。"
  value       = module.frontend.url
}

output "frontend_distribution_id" {
  description = "フロントの配信設定・キャッシュ更新に使う CloudFront Distribution ID。"
  value       = module.frontend.distribution_id
}

output "frontend_distribution_arn" {
  description = "フロント用 CloudFront Distribution ARN。"
  value       = module.frontend.distribution_arn
}

output "frontend_deployment" {
  description = "配信環境の確認用設定。S3 配置 Bash は bootstrap の frontend_deployments を参照します。"
  value = {
    environment    = "prod"
    aws_account_id = var.aws_account_id
    aws_region     = var.aws_region
    bucket_name    = module.frontend.bucket_name
    url            = module.frontend.url
  }
}

output "application_parameter_names" {
  description = "環境変数名から Parameter Store の名前を引ける map。"
  value       = module.application_config.parameter_names
}

output "application_parameter_arns" {
  description = "ECS 等へ設定値を渡すための Parameter Store ARN の map。"
  value       = module.application_config.parameter_arns
}

output "application_config_values" {
  description = "バケット名・公開 URL 等の非機密設定値。Secrets Manager の秘密値は含めません。"
  value       = module.application_config.values
}

output "ecr_repository_url" {
  description = "バックエンドのコンテナイメージを push する ECR リポジトリの URL。"
  value       = data.aws_ecr_repository.backend.repository_url
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
  description = "バックエンドのサービス用タスク定義 ARN。"
  value       = module.ecs.task_definition_arn
}

output "ecs_migration" {
  description = "DB migration の専用タスク定義・private subnet・ログ等の実行設定。秘密値は含めません。"
  value       = module.ecs.migration
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
  description = "Django SECRET_KEY の ARN。値が未登録の場合は apply 内で自動生成・登録します。"
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

output "deletion_policy" {
  description = "この環境の ALB・RDS・S3・ECR・Secret に設定する削除方針。"
  value = {
    alb_deletion_protection               = module.alb.deletion_protection
    rds_deletion_protection               = module.rds.deletion_policy.deletion_protection
    db_skip_final_snapshot                = module.rds.deletion_policy.skip_final_snapshot
    frontend_force_destroy                = module.frontend.force_destroy
    ecr_force_delete                      = false
    django_secret_recovery_window_in_days = module.ecs.django_secret_recovery_window_in_days
  }
}

