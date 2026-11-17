resource "aws_ecs_cluster" "main" {
  name = var.name

  setting {
    name  = "containerInsights"
    value = "disabled"
  }
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  container_definitions = jsonencode([local.backend_container])
}

resource "aws_ecs_service" "backend" {
  name             = "${var.name}-backend"
  cluster          = aws_ecs_cluster.main.id
  task_definition  = aws_ecs_task_definition.backend.arn
  desired_count    = var.desired_count
  launch_type      = "FARGATE"
  platform_version = "1.4.0"

  health_check_grace_period_seconds  = 60
  deployment_minimum_healthy_percent = 100
  deployment_maximum_percent         = 200
  wait_for_steady_state              = true
  # ARN が同じままパラメータの値だけ変わった場合も、新しい値でタスクを起動し直す。
  # 時刻ではなく設定値のハッシュなので、変更のない apply では再デプロイしない。
  force_new_deployment = true
  triggers = {
    application_config_revision = var.application_config_revision
  }
  enable_ecs_managed_tags = true
  propagate_tags          = "SERVICE"

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [var.security_group_id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = var.target_group_arn
    container_name   = "backend"
    container_port   = var.container_port
  }

  # Network and listener readiness is carried by the input outputs.
  depends_on = [aws_iam_role_policy.ecs_execution, aws_iam_role_policy.ecs_uploads, terraform_data.migration]
}
