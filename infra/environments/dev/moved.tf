# Preserve existing state addresses when adopting the module structure.
# Keep these mappings for environments that have not yet applied the refactor.

moved {
  from = aws_vpc.main
  to   = module.network.aws_vpc.main
}

moved {
  from = aws_internet_gateway.main
  to   = module.network.aws_internet_gateway.main
}

moved {
  from = aws_subnet.public
  to   = module.network.aws_subnet.public
}

moved {
  from = aws_subnet.app
  to   = module.network.aws_subnet.app
}

moved {
  from = aws_subnet.db
  to   = module.network.aws_subnet.db
}

moved {
  from = aws_route_table.public
  to   = module.network.aws_route_table.public
}

moved {
  from = aws_route.public_internet
  to   = module.network.aws_route.public_internet
}

moved {
  from = aws_route_table_association.public
  to   = module.network.aws_route_table_association.public
}

moved {
  from = aws_eip.nat
  to   = module.network.aws_eip.nat
}

moved {
  from = aws_nat_gateway.main
  to   = module.network.aws_nat_gateway.main
}

moved {
  from = aws_route_table.app
  to   = module.network.aws_route_table.app
}

moved {
  from = aws_route.app_nat
  to   = module.network.aws_route.app_nat
}

moved {
  from = aws_route_table_association.app
  to   = module.network.aws_route_table_association.app
}

moved {
  from = aws_route_table.db
  to   = module.network.aws_route_table.db
}

moved {
  from = aws_route_table_association.db
  to   = module.network.aws_route_table_association.db
}

moved {
  from = aws_security_group.alb
  to   = module.network.aws_security_group.alb
}

moved {
  from = aws_vpc_security_group_ingress_rule.alb_http
  to   = module.network.aws_vpc_security_group_ingress_rule.alb_http
}

moved {
  from = aws_vpc_security_group_ingress_rule.alb_https
  to   = module.network.aws_vpc_security_group_ingress_rule.alb_https
}

moved {
  from = aws_vpc_security_group_egress_rule.alb_to_ecs
  to   = module.network.aws_vpc_security_group_egress_rule.alb_to_ecs
}

moved {
  from = aws_security_group.ecs
  to   = module.network.aws_security_group.ecs
}

moved {
  from = aws_vpc_security_group_ingress_rule.ecs_from_alb
  to   = module.network.aws_vpc_security_group_ingress_rule.ecs_from_alb
}

moved {
  from = aws_vpc_security_group_egress_rule.ecs_https
  to   = module.network.aws_vpc_security_group_egress_rule.ecs_https
}

moved {
  from = aws_vpc_security_group_egress_rule.ecs_to_rds
  to   = module.network.aws_vpc_security_group_egress_rule.ecs_to_rds
}

moved {
  from = aws_security_group.rds
  to   = module.network.aws_security_group.rds
}

moved {
  from = aws_vpc_security_group_ingress_rule.rds_from_ecs
  to   = module.network.aws_vpc_security_group_ingress_rule.rds_from_ecs
}

moved {
  from = aws_lb.main
  to   = module.alb.aws_lb.main
}

moved {
  from = aws_lb_target_group.backend
  to   = module.alb.aws_lb_target_group.backend
}

moved {
  from = aws_lb_listener.http
  to   = module.alb.aws_lb_listener.http
}

moved {
  from = aws_lb_listener.https
  to   = module.alb.aws_lb_listener.https
}

moved {
  from = aws_ecr_repository.backend
  to   = module.ecr.aws_ecr_repository.backend
}

moved {
  from = aws_ecr_lifecycle_policy.backend
  to   = module.ecr.aws_ecr_lifecycle_policy.backend
}

moved {
  from = aws_db_subnet_group.main
  to   = module.rds.aws_db_subnet_group.main
}

moved {
  from = aws_db_instance.main
  to   = module.rds.aws_db_instance.main
}

moved {
  from = aws_ecs_cluster.main
  to   = module.ecs.aws_ecs_cluster.main
}

moved {
  from = aws_ecs_task_definition.backend
  to   = module.ecs.aws_ecs_task_definition.backend
}

moved {
  from = aws_ecs_service.backend
  to   = module.ecs.aws_ecs_service.backend
}

moved {
  from = aws_iam_role.ecs_execution
  to   = module.ecs.aws_iam_role.ecs_execution
}

moved {
  from = aws_iam_role_policy.ecs_execution
  to   = module.ecs.aws_iam_role_policy.ecs_execution
}

moved {
  from = aws_iam_role.ecs_task
  to   = module.ecs.aws_iam_role.ecs_task
}

moved {
  from = aws_cloudwatch_log_group.backend
  to   = module.ecs.aws_cloudwatch_log_group.backend
}

moved {
  from = aws_secretsmanager_secret.django
  to   = module.ecs.aws_secretsmanager_secret.django
}
