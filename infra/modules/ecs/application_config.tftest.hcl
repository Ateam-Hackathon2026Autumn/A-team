# モック上でタスク定義と IAM の入力を確認する。ECS・SSM に実際の通信はしない。
mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }

  mock_resource "aws_secretsmanager_secret" {
    defaults = { arn = "arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:a-team-dev/django-test-ABC123" }
  }

  mock_resource "aws_cloudwatch_log_group" {
    defaults = { arn = "arn:aws:logs:ap-northeast-1:123456789012:log-group:/ecs/a-team-dev/backend" }
  }

  mock_resource "aws_ecs_task_definition" {
    defaults = { arn = "arn:aws:ecs:ap-northeast-1:123456789012:task-definition/a-team-dev-backend:1" }
  }
}

override_resource {
  target = aws_iam_role.ecs_execution
  values = { arn = "arn:aws:iam::123456789012:role/a-team-dev-ecs-execution" }
}

override_resource {
  target = aws_iam_role.ecs_task
  values = { arn = "arn:aws:iam::123456789012:role/a-team-dev-ecs-task" }
}

override_resource {
  target = aws_ecs_task_definition.migration
  values = { arn = "arn:aws:ecs:ap-northeast-1:123456789012:task-definition/a-team-dev-migration:1" }
}

variables {
  name              = "a-team-dev"
  aws_region        = "ap-northeast-1"
  aws_account_id    = "123456789012"
  subnet_ids        = ["subnet-0123456789abcdef0"]
  security_group_id = "sg-0123456789abcdef0"
  target_group_arn  = "arn:aws:elasticloadbalancing:ap-northeast-1:123456789012:targetgroup/backend/0123456789abcdef"
  ecr_repository = {
    url = "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/a-team-dev/backend"
    arn = "arn:aws:ecr:ap-northeast-1:123456789012:repository/a-team-dev/backend"
  }
  uploads_bucket_name = "a-team-uploads-tests"
  database = {
    host        = "database-tests.rds.amazonaws.com"
    port        = 3306
    name        = "hackathon"
    username    = "appadmin"
    secret_arn  = "arn:aws:secretsmanager:ap-northeast-1:123456789012:secret:rds-tests-ABC123"
    resource_id = "db-READINESSTESTS"
  }
  container_port       = 8000
  image_tag            = "test-001"
  desired_count        = 0
  django_allowed_hosts = ["*"]
  application_parameter_arns = {
    AWS_STORAGE_BUCKET_NAME      = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/uploads-bucket-name"
    FRONTEND_BASE_URL            = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/frontend-base-url"
    DJANGO_PUBLIC_IMAGE_BASE_URL = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/public-image-base-url"
    DJANGO_CSRF_TRUSTED_ORIGINS  = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/csrf-trusted-origins"
    DJANGO_COOKIE_SECURE         = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/django-cookie-secure"
  }
  application_config_revision = sha256("initial-settings")
}

run "inject_parameters_and_keep_existing_secrets" {
  command = apply

  assert {
    condition = (
      length(jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].secrets) == 7 &&
      alltrue([for name, arn in var.application_parameter_arns :
        one([for secret in jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].secrets : secret.valueFrom if secret.name == name]) == arn
      ]) &&
      one([for secret in jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].secrets : secret.valueFrom if secret.name == "DB_PASSWORD"]) == "${var.database.secret_arn}:password::" &&
      one([for secret in jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].secrets : secret.valueFrom if secret.name == "DJANGO_SECRET_KEY"]) == aws_secretsmanager_secret.django.arn
    )
    error_message = "SSM 設定を正しい名前で注入し、既存の DB・Django の秘密値の参照も残す必要があります。"
  }

  assert {
    condition = anytrue([for statement in data.aws_iam_policy_document.ecs_uploads.statement :
      statement.sid == "ReadAndWriteUploads" &&
      contains(statement.resources, "arn:aws:s3:::${var.uploads_bucket_name}/images/*") &&
      contains(statement.actions, "s3:PutObject") && contains(statement.actions, "s3:GetObject")
    ])
    error_message = "ECS からアップロードバケットの images/ を読み書きできる必要があります。"
  }

  assert {
    condition = (
      alltrue([for environment in jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].environment :
        !contains(concat(keys(var.application_parameter_arns), ["UPLOADS_BUCKET_NAME"]), environment.name)
      ]) &&
      one([for environment in jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].environment : environment.value if environment.name == "AWS_S3_REGION_NAME"]) == var.aws_region
    )
    error_message = "同じ環境変数を通常設定と SSM の両方で定義せず、S3 の設定名をバック側へ合わせる必要があります。"
  }

  assert {
    condition = (
      one([for statement in data.aws_iam_policy_document.ecs_execution.statement : statement.actions if statement.sid == "ReadApplicationParameters"]) == toset(["ssm:GetParameters"]) &&
      one([for statement in data.aws_iam_policy_document.ecs_execution.statement : statement.resources if statement.sid == "ReadApplicationParameters"]) == toset(values(var.application_parameter_arns)) &&
      aws_iam_role_policy.ecs_execution.role == aws_iam_role.ecs_execution.id
    )
    error_message = "実行ロールに、対象の4 ARN だけを読む権限を付与する必要があります。"
  }

  assert {
    condition = (
      aws_ecs_service.backend.force_new_deployment &&
      aws_ecs_service.backend.triggers["application_config_revision"] == var.application_config_revision &&
      aws_ecs_service.backend.desired_count == 0
    )
    error_message = "設定変更時の再デプロイを有効にし、初期のサービス起動数0を維持する必要があります。"
  }
}

run "configuration_change_triggers_redeployment" {
  command = plan

  variables {
    application_config_revision = sha256("updated-settings")
  }

  assert {
    condition     = aws_ecs_service.backend.triggers["application_config_revision"] == sha256("updated-settings")
    error_message = "SSM の値だけを変更した場合にも ECS の再デプロイ条件を更新する必要があります。"
  }
}

run "reject_parameters_in_another_account" {
  command = plan

  variables {
    application_parameter_arns = {
      AWS_STORAGE_BUCKET_NAME      = "arn:aws:ssm:ap-northeast-1:999999999999:parameter/other/uploads"
      FRONTEND_BASE_URL            = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/frontend-base-url"
      DJANGO_PUBLIC_IMAGE_BASE_URL = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/public-image-base-url"
      DJANGO_CSRF_TRUSTED_ORIGINS  = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/csrf-trusted-origins"
      DJANGO_COOKIE_SECURE         = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/django-cookie-secure"
    }
  }

  expect_failures = [var.application_parameter_arns]
}

run "migration_uses_the_same_release_database_and_private_network" {
  command = apply

  assert {
    condition = (
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].name == "migration" &&
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].command == ["python", "manage.py", "migrate", "--noinput"] &&
      length(jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].portMappings) == 0 &&
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].image == jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].image &&
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].environment == jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].environment &&
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].secrets == jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].secrets &&
      aws_ecs_task_definition.migration.execution_role_arn == aws_ecs_task_definition.backend.execution_role_arn &&
      aws_ecs_task_definition.migration.task_role_arn == aws_ecs_task_definition.backend.task_role_arn &&
      aws_ecs_task_definition.migration.runtime_platform[0].cpu_architecture == "X86_64" &&
      aws_ecs_service.backend.task_definition == aws_ecs_task_definition.backend.arn
    )
    error_message = "migration はサーバーを起動せず、バックと同じイメージ・DB 接続・Secret・ロールで migrate する必要があります。"
  }

  assert {
    condition = (
      output.migration.task_definition == aws_ecs_task_definition.migration.arn &&
      output.migration.task_definition != aws_ecs_service.backend.task_definition &&
      output.migration.cluster == aws_ecs_cluster.main.name &&
      output.migration.service == aws_ecs_service.backend.name &&
      output.migration.aws_account_id == var.aws_account_id &&
      output.migration.aws_region == var.aws_region &&
      output.migration.network_configuration.awsvpcConfiguration.subnets == var.subnet_ids &&
      output.migration.network_configuration.awsvpcConfiguration.securityGroups == [var.security_group_id] &&
      output.migration.network_configuration.awsvpcConfiguration.assignPublicIp == "DISABLED" &&
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].logConfiguration.options["awslogs-stream-prefix"] == "migration"
    )
    error_message = "単発タスクは専用 ARN・既存の private subnet / SG と migration 用ログの設定を output する必要があります。"
  }
}

run "development_seed_runs_after_migrate" {
  command = plan

  variables {
    migration_load_initial_data = true
    migration_load_dev_seed     = true
  }

  assert {
    condition = (
      jsondecode(aws_ecs_task_definition.migration.container_definitions)[0].command == [
        "sh", "-c",
        "python manage.py migrate --noinput && DJANGO_DEBUG=true python manage.py seed_dev >/dev/null && echo 'Development seed completed.'",
      ] &&
      !output.migration.load_initial_data &&
      one([for item in jsondecode(aws_ecs_task_definition.backend.container_definitions)[0].environment : item.value if item.name == "DJANGO_DEBUG"]) == "false"
    )
    error_message = "migrate 成功後だけ seed_dev を実行し、Web サービスの DEBUG は無効にする必要があります。"
  }
}

# ここは plan のみ。apply のテストでは desired_count=0 とし、local-exec を起動しない。
run "automatic_migration_gates_running_service" {
  command = plan

  variables {
    desired_count = 1
    image_digest  = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }

  assert {
    condition = (
      length(terraform_data.django_secret_ready) == 1 &&
      length(terraform_data.migration) == 1 &&
      contains(terraform_data.migration[0].triggers_replace, var.database.resource_id) &&
      contains(terraform_data.migration[0].triggers_replace, aws_ecs_task_definition.migration.arn) &&
      output.migration.image == "${var.ecr_repository.url}@${var.image_digest}" &&
      aws_ecs_service.backend.desired_count == 1
    )
    error_message = "起動数1では Secret 準備・migration を実行し、DB 再作成・イメージ更新に追従する必要があります。"
  }
}
