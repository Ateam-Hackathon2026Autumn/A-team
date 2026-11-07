# Compose shared modules here. Environment defaults live in variables.tf and tfvars.
module "network" {
  source = "../../modules/network"

  name               = local.name
  aws_region         = var.aws_region
  vpc_cidr           = var.vpc_cidr
  single_nat_gateway = var.single_nat_gateway
  alb_ingress_cidrs  = var.alb_ingress_cidrs
  https_enabled      = var.certificate_arn != null
  container_port     = var.container_port
}

module "alb" {
  source = "../../modules/alb"

  name                = local.name
  vpc_id              = module.network.vpc_id
  subnet_ids          = module.network.public_subnet_ids
  security_group_id   = module.network.alb_security_group_id
  container_port      = var.container_port
  certificate_arn     = var.certificate_arn
  deletion_protection = var.deletion_protection
}

module "ecr" {
  source = "../../modules/ecr"

  name = local.name
}

module "rds" {
  source = "../../modules/rds"

  name                         = local.name
  subnet_ids                   = module.network.db_subnet_ids
  security_group_id            = module.network.rds_security_group_id
  db_name                      = var.db_name
  db_username                  = var.db_username
  db_engine_version            = var.db_engine_version
  db_instance_class            = var.db_instance_class
  db_multi_az                  = var.db_multi_az
  deletion_protection          = var.deletion_protection
  db_skip_final_snapshot       = var.db_skip_final_snapshot
  db_final_snapshot_identifier = var.db_final_snapshot_identifier
}

module "ecs" {
  source = "../../modules/ecs"

  name                = local.name
  aws_region          = var.aws_region
  aws_account_id      = var.aws_account_id
  subnet_ids          = module.network.app_subnet_ids
  security_group_id   = module.network.ecs_security_group_id
  target_group_arn    = module.alb.target_group_arn
  ecr_repository      = module.ecr.repository
  uploads_bucket_name = var.uploads_bucket_name
  image_prefixes = {
    input  = var.image_compression.input_prefix
    output = var.image_compression.output_prefix
  }
  database             = module.rds.connection
  container_port       = var.container_port
  image_tag            = var.image_tag
  desired_count        = var.desired_count
  django_allowed_hosts = var.django_allowed_hosts
}
