locals {
  # Stable keys keep resource addresses independent of AZ ordering.
  subnets = {
    a = {
      availability_zone = "${var.aws_region}a"
      public_cidr       = cidrsubnet(var.vpc_cidr, 8, 0)
      app_cidr          = cidrsubnet(var.vpc_cidr, 8, 10)
      db_cidr           = cidrsubnet(var.vpc_cidr, 8, 20)
    }
    c = {
      availability_zone = "${var.aws_region}c"
      public_cidr       = cidrsubnet(var.vpc_cidr, 8, 1)
      app_cidr          = cidrsubnet(var.vpc_cidr, 8, 11)
      db_cidr           = cidrsubnet(var.vpc_cidr, 8, 21)
    }
  }

  nat_subnets = var.single_nat_gateway ? { a = local.subnets.a } : local.subnets
}
