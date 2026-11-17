# 単発実行専用。サービスや定期スケジュールには関連付けない。
# ECR の同じリリースを使い、コンテナ終了時にタスクも停止する。
resource "aws_ecs_task_definition" "migration" {
  family                   = "${var.name}-migration"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = aws_ecs_task_definition.backend.cpu
  memory                   = aws_ecs_task_definition.backend.memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([merge(local.backend_container, {
    name         = "migration"
    command      = ["python", "manage.py", "migrate", "--noinput"]
    portMappings = []
    logConfiguration = merge(local.backend_container.logConfiguration, {
      options = merge(local.backend_container.logConfiguration.options, {
        awslogs-stream-prefix = "migration"
      })
    })
  })])

  depends_on = [aws_iam_role_policy.ecs_execution, aws_iam_role_policy.ecs_uploads]
}

locals {
  # サービスの resource を参照しない。サービス作成前に実行できる依存関係にする。
  migration_config = {
    aws_account_id     = var.aws_account_id
    aws_region         = var.aws_region
    cluster            = aws_ecs_cluster.main.name
    service            = "${var.name}-backend"
    task_definition    = aws_ecs_task_definition.migration.arn
    container_name     = "migration"
    image              = local.backend_container.image
    execution_role_arn = aws_iam_role.ecs_execution.arn
    task_role_arn      = aws_iam_role.ecs_task.arn
    network_configuration = {
      awsvpcConfiguration = {
        subnets        = var.subnet_ids
        securityGroups = [var.security_group_id]
        assignPublicIp = "DISABLED"
      }
    }
    log_group         = aws_cloudwatch_log_group.backend.name
    log_stream_prefix = "migration"
    load_initial_data = var.migration_load_initial_data
    timeout_seconds   = var.migration_timeout_seconds
  }

  deployment_profile_environment = var.deployment_aws_profile == null ? {} : {
    AWS_PROFILE         = var.deployment_aws_profile
    AWS_DEFAULT_PROFILE = var.deployment_aws_profile
  }
}

# 起動数0は基盤だけの準備・停止用。1以上の作成/更新では必ず成功を待つ。
resource "terraform_data" "django_secret_ready" {
  count = var.desired_count > 0 ? 1 : 0

  triggers_replace = [
    aws_secretsmanager_secret.django.arn,
    filesha256("${path.module}/../../scripts/ensure_django_secret.py"),
  ]

  provisioner "local-exec" {
    command = "python3 \"$DEPLOY_SCRIPT\""
    quiet   = true
    environment = merge(local.deployment_profile_environment, {
      DEPLOY_SCRIPT = abspath("${path.module}/../../scripts/ensure_django_secret.py")
      DEPLOY_CONFIG_JSON = jsonencode({
        aws_account_id = var.aws_account_id
        aws_region     = var.aws_region
        secret_arn     = aws_secretsmanager_secret.django.arn
      })
    })
  }
}

resource "terraform_data" "migration" {
  count = var.desired_count > 0 ? 1 : 0

  triggers_replace = [
    aws_ecs_task_definition.migration.arn,
    var.database.resource_id,
    var.application_config_revision,
    var.migration_load_initial_data,
    var.migration_timeout_seconds,
    terraform_data.django_secret_ready[0].id,
    filesha256("${path.module}/../../scripts/run_migration.py"),
  ]

  provisioner "local-exec" {
    command = "python3 \"$DEPLOY_SCRIPT\" --from-terraform"
    quiet   = true
    environment = merge(local.deployment_profile_environment, {
      DEPLOY_SCRIPT      = abspath("${path.module}/../../scripts/run_migration.py")
      DEPLOY_CONFIG_JSON = jsonencode(local.migration_config)
    })
  }

  # on_failure=continue は指定しない。失敗した場合はサービス作成・更新へ進まない。
  depends_on = [terraform_data.django_secret_ready, aws_iam_role_policy.ecs_execution, aws_iam_role_policy.ecs_uploads]
}
