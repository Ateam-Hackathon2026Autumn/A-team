# バケットポリシーは bootstrap で管理し、環境ごとの配信許可だけをここで管理する。
resource "aws_s3_access_point" "images" {
  count = var.uploads_bucket_name == null ? 0 : 1

  bucket = var.uploads_bucket_name
  name   = "${var.name}-public-images"

  public_access_block_configuration {
    block_public_acls       = true
    block_public_policy     = true
    ignore_public_acls      = true
    restrict_public_buckets = true
  }

  lifecycle {
    ignore_changes = [policy]
  }
}

resource "aws_s3control_access_point_policy" "images" {
  count = length(aws_s3_access_point.images)

  access_point_arn = aws_s3_access_point.images[count.index].arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "AllowThisCloudFrontToReadPublicImages"
      Effect    = "Allow"
      Principal = { Service = "cloudfront.amazonaws.com" }
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_access_point.images[count.index].arn}/object/images/*"
      Condition = {
        StringEquals = { "AWS:SourceArn" = aws_cloudfront_distribution.site.arn }
      }
    }]
  })
}
