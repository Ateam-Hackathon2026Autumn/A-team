output "vpc_id" {
  description = "アプリ用 VPC の ID。"
  value       = aws_vpc.main.id
}

output "public_subnet_ids" {
  description = "インターネット向けルートの設定が完了した public subnet の ID 一覧。"
  value       = [for subnet in aws_subnet.public : subnet.id]

  depends_on = [aws_route.public_internet, aws_route_table_association.public]
}

output "app_subnet_ids" {
  description = "NAT 経由のルート設定が完了したアプリ用 private subnet の ID 一覧。"
  value       = [for subnet in aws_subnet.app : subnet.id]

  depends_on = [
    aws_route.public_internet,
    aws_route_table_association.public,
    aws_route.app_nat,
    aws_route_table_association.app,
  ]
}

output "db_subnet_ids" {
  description = "外向きルートを持たない DB 用サブネットの ID 一覧。"
  value       = [for subnet in aws_subnet.db : subnet.id]

  depends_on = [aws_route_table_association.db]
}

output "alb_security_group_id" {
  description = "リスナーへの受信とターゲットへの送信の許可設定が完了した ALB 用セキュリティグループの ID。"
  value       = aws_security_group.alb.id

  depends_on = [
    aws_vpc_security_group_ingress_rule.alb_http,
    aws_vpc_security_group_ingress_rule.alb_https,
    aws_vpc_security_group_egress_rule.alb_to_ecs,
  ]
}

output "ecs_security_group_id" {
  description = "ALB からの受信、外部 HTTPS 通信、DB 接続の許可設定が完了した ECS 用セキュリティグループの ID。"
  value       = aws_security_group.ecs.id

  depends_on = [
    aws_vpc_security_group_ingress_rule.ecs_from_alb,
    aws_vpc_security_group_egress_rule.ecs_https,
    aws_vpc_security_group_egress_rule.ecs_to_rds,
    aws_vpc_security_group_ingress_rule.rds_from_ecs,
    aws_vpc_security_group_egress_rule.alb_to_ecs,
  ]
}

output "rds_security_group_id" {
  description = "ECS からの接続許可が設定済みの RDS 用セキュリティグループの ID。"
  value       = aws_security_group.rds.id

  depends_on = [aws_vpc_security_group_ingress_rule.rds_from_ecs]
}
