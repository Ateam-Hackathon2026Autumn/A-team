# ローカルから署名なしの固定 URL を検証するための画像専用バケット。
resource "aws_s3_bucket" "test_uploads" {
  bucket        = "${var.project_name}-test-uploads-${var.aws_account_id}-${var.aws_region}"
  force_destroy = false
  tags          = { Purpose = "test-image-uploads" }
}

resource "aws_s3_bucket_ownership_controls" "test_uploads" {
  bucket = aws_s3_bucket.test_uploads.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "test_uploads" {
  bucket = aws_s3_bucket.test_uploads.id

  # 公開範囲はバケットポリシーの GET に限定する。オブジェクト ACL は無効のまま。
  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = false
  restrict_public_buckets = false
}

data "aws_iam_policy_document" "test_uploads_bucket" {
  statement {
    sid       = "ReadTestImages"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.test_uploads.arn}/images/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }
  }

  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.test_uploads.arn, "${aws_s3_bucket.test_uploads.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "test_uploads" {
  bucket     = aws_s3_bucket.test_uploads.id
  policy     = data.aws_iam_policy_document.test_uploads_bucket.json
  depends_on = [aws_s3_bucket_public_access_block.test_uploads]
}

data "aws_iam_policy_document" "test_uploads_writer" {
  statement {
    sid       = "ReadAndWriteTestImages"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:DeleteObject"]
    resources = ["${aws_s3_bucket.test_uploads.arn}/images/*"]
  }
}

resource "aws_iam_policy" "test_uploads_writer" {
  name        = "${var.project_name}-test-uploads-writer"
  description = "Read and upload images in the test uploads bucket"
  policy      = data.aws_iam_policy_document.test_uploads_writer.json
}

output "test_uploads" {
  description = "ローカル検証用 S3 の名前・画像 URL の基点・Django 用の IAM ポリシー ARN。"
  value = {
    bucket_name       = aws_s3_bucket.test_uploads.id
    base_url          = "https://${aws_s3_bucket.test_uploads.bucket_regional_domain_name}"
    writer_policy_arn = aws_iam_policy.test_uploads_writer.arn
  }
}
