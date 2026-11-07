resource "aws_db_subnet_group" "main" {
  name       = var.name
  subnet_ids = var.subnet_ids
}

resource "aws_db_instance" "main" {
  identifier     = var.name
  engine         = "mysql"
  engine_version = var.db_engine_version
  instance_class = var.db_instance_class
  db_name        = var.db_name
  username       = var.db_username
  port           = 3306

  # AWS generates/stores the password; its value never enters Terraform state.
  manage_master_user_password = true

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [var.security_group_id]
  publicly_accessible    = false
  multi_az               = var.db_multi_az

  backup_retention_period         = 7
  backup_window                   = "17:00-18:00"
  maintenance_window              = "sun:18:00-sun:19:00"
  auto_minor_version_upgrade      = true
  apply_immediately               = false
  copy_tags_to_snapshot           = true
  enabled_cloudwatch_logs_exports = ["error", "slowquery"]

  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.db_skip_final_snapshot
  final_snapshot_identifier = var.db_final_snapshot_identifier

  lifecycle {
    precondition {
      condition     = var.db_skip_final_snapshot || var.db_final_snapshot_identifier != null
      error_message = "Set a unique db_final_snapshot_identifier when retaining a final snapshot."
    }
  }
}
