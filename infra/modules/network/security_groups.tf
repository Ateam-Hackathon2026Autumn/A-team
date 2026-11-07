# AWS の文字種制限に合わせ、SG とルールの description は英語、日本語の説明はコメントに記載します。
resource "aws_security_group" "alb" {
  name_prefix = "${var.name}-alb-"
  # インターネットから HTTP / HTTPS 接続を受け付ける ALB 用。
  description = "Public HTTP(S) entry point"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.name}-alb" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "alb_http" {
  for_each = var.alb_ingress_cidrs

  security_group_id = aws_security_group.alb.id
  # HTTP 接続を受け付けます。証明書がある場合はリスナー側で HTTPS にリダイレクトします。
  description = "HTTP or redirect to HTTPS"
  cidr_ipv4   = each.value
  ip_protocol = "tcp"
  from_port   = 80
  to_port     = 80
}

resource "aws_vpc_security_group_ingress_rule" "alb_https" {
  for_each = var.https_enabled ? var.alb_ingress_cidrs : toset([])

  security_group_id = aws_security_group.alb.id
  # HTTPS 接続を受け付けます。
  description = "HTTPS"
  cidr_ipv4   = each.value
  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443
}

resource "aws_vpc_security_group_egress_rule" "alb_to_ecs" {
  security_group_id            = aws_security_group.alb.id
  referenced_security_group_id = aws_security_group.ecs.id
  ip_protocol                  = "tcp"
  from_port                    = var.container_port
  to_port                      = var.container_port
}

resource "aws_security_group" "ecs" {
  name_prefix = "${var.name}-ecs-"
  # ALB からのみ接続を許可するバックエンドタスク用。
  description = "Backend tasks, reachable only from ALB"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.name}-ecs" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "ecs_from_alb" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.container_port
  to_port                      = var.container_port
}

resource "aws_vpc_security_group_egress_rule" "ecs_https" {
  security_group_id = aws_security_group.ecs.id
  # NAT 経由で ECR・CloudWatch Logs・Secrets Manager・外部 HTTPS API に接続します。
  description = "ECR, CloudWatch Logs, Secrets Manager and external HTTPS APIs through NAT"
  cidr_ipv4   = "0.0.0.0/0"
  ip_protocol = "tcp"
  from_port   = 443
  to_port     = 443
}

resource "aws_vpc_security_group_egress_rule" "ecs_to_rds" {
  security_group_id            = aws_security_group.ecs.id
  referenced_security_group_id = aws_security_group.rds.id
  ip_protocol                  = "tcp"
  from_port                    = 3306
  to_port                      = 3306
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.name}-rds-"
  # バックエンドタスクからのみ MySQL 接続を許可する RDS 用。
  description = "MySQL, reachable only from backend tasks"
  vpc_id      = aws_vpc.main.id
  tags        = { Name = "${var.name}-rds" }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "rds_from_ecs" {
  security_group_id            = aws_security_group.rds.id
  referenced_security_group_id = aws_security_group.ecs.id
  ip_protocol                  = "tcp"
  from_port                    = 3306
  to_port                      = 3306
}
