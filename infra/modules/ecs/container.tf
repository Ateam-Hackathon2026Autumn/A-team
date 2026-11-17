# サービスと migration は同じイメージ・環境変数・Secret・ログ設定を使う。
# 接続設定を別々に定義すると、異なる DB や異なるリリースへ migrate する原因になる。
locals {
  backend_container = {
    name      = "backend"
    image     = var.image_digest == null ? "${var.ecr_repository.url}:${var.image_tag}" : "${var.ecr_repository.url}@${var.image_digest}"
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
      { name = "AWS_S3_REGION_NAME", value = var.aws_region },
      { name = "UPLOADS_PREFIX", value = "uploads/" },
      { name = "IMAGE_INPUT_PREFIX", value = var.image_prefixes.input },
      { name = "IMAGE_OUTPUT_PREFIX", value = var.image_prefixes.output },
      { name = "DB_HOST", value = var.database.host },
      { name = "DB_PORT", value = tostring(var.database.port) },
      { name = "DB_NAME", value = var.database.name },
      { name = "DB_USER", value = var.database.username },
    ]

    # secrets は Parameter Store の String にも利用できる。値は起動時に実行ロールが取得する。
    secrets = concat([
      {
        name      = "DB_PASSWORD"
        valueFrom = "${var.database.secret_arn}:password::"
      },
      {
        name      = "DJANGO_SECRET_KEY"
        valueFrom = aws_secretsmanager_secret.django.arn
      },
      ], [for name, arn in var.application_parameter_arns : {
        name      = name
        valueFrom = arn
    }])

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.backend.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
  }
}
