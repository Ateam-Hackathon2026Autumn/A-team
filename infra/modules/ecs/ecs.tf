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

  container_definitions = jsonencode([{
    name      = "backend"
    image     = "${var.ecr_repository.url}:${var.image_tag}"
    essential = true

    portMappings = [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }]

    environment = [
      { name = "DJANGO_DEBUG", value = "false" },
      { name = "DJANGO_ALLOWED_HOSTS", value = join(",", var.django_allowed_hosts) },
      { name = "AWS_DEFAULT_REGION", value = var.aws_region },
      { name = "UPLOADS_BUCKET_NAME", value = var.uploads_bucket_name },
      { name = "UPLOADS_PREFIX", value = "uploads/" },
      { name = "IMAGE_INPUT_PREFIX", value = var.image_prefixes.input },
      { name = "IMAGE_OUTPUT_PREFIX", value = var.image_prefixes.output },
      { name = "DB_HOST", value = var.database.host },
      { name = "DB_PORT", value = tostring(var.database.port) },
      { name = "DB_NAME", value = var.database.name },
      { name = "DB_USER", value = var.database.username },
    ]

    secrets = [
      {
        name      = "DB_PASSWORD"
        valueFrom = "${var.database.secret_arn}:password::"
      },
      {
        name      = "DJANGO_SECRET_KEY"
        valueFrom = aws_secretsmanager_secret.django.arn
      },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.backend.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
  }])
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
  enable_ecs_managed_tags            = true
  propagate_tags                     = "SERVICE"

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
  depends_on = [aws_iam_role_policy.ecs_execution, aws_iam_role_policy.ecs_uploads]
}
