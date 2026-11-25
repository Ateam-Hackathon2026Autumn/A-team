variable "bucket_name" {
  description = "保持するフロント成果物専用のバケット名。既存環境から移す場合も同じ名前を指定します。"
  type        = string

  validation {
    condition     = can(regex("^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$", var.bucket_name))
    error_message = "bucket_name は3〜63文字の英小文字・数字・ハイフンにしてください。"
  }
}

resource "aws_s3_bucket" "site" {
  bucket        = var.bucket_name
  force_destroy = false
  tags          = { Purpose = "frontend-assets" }

  lifecycle { prevent_destroy = true }
}

resource "aws_s3_bucket_ownership_controls" "site" {
  bucket = aws_s3_bucket.site.id
  rule { object_ownership = "BucketOwnerEnforced" }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "site" {
  bucket = aws_s3_bucket.site.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}

resource "aws_s3_bucket_public_access_block" "site" {
  bucket                  = aws_s3_bucket.site.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# CloudFront の ARN を条件に使うため、バケットポリシーだけは環境側で一元管理する。
# bootstrap から同じバケットに別の aws_s3_bucket_policy を追加しない。
output "bucket_name" {
  description = "ビルド成果物の配置先。"
  value       = aws_s3_bucket.site.bucket
}
