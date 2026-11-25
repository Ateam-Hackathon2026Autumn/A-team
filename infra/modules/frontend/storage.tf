# S3 本体・セキュリティ設定は bootstrap 管理。配信元として既存バケットを読む。
data "aws_s3_bucket" "site" {
  bucket = var.bucket_name
}

# 旧環境 state の S3 を削除せず bootstrap に引き継ぐ。CloudFront と policy は移動しない。
removed {
  from = aws_s3_bucket.site
  lifecycle { destroy = false }
}

removed {
  from = aws_s3_bucket_ownership_controls.site
  lifecycle { destroy = false }
}

removed {
  from = aws_s3_bucket_server_side_encryption_configuration.site
  lifecycle { destroy = false }
}

removed {
  from = aws_s3_bucket_public_access_block.site
  lifecycle { destroy = false }
}

# バケットポリシーの管理元はこのリソースだけ。CloudFront を作り直すと ARN も追従する。
resource "aws_s3_bucket_policy" "site" {
  bucket = data.aws_s3_bucket.site.bucket
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowOnlyThisCloudFrontDistribution"
        Effect    = "Allow"
        Principal = { Service = "cloudfront.amazonaws.com" }
        Action    = "s3:GetObject"
        Resource  = "${data.aws_s3_bucket.site.arn}/*"
        Condition = {
          StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.site.arn }
        }
      },
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource  = [data.aws_s3_bucket.site.arn, "${data.aws_s3_bucket.site.arn}/*"]
        Condition = { Bool = { "aws:SecureTransport" = "false" } }
      },
    ]
  })

}
