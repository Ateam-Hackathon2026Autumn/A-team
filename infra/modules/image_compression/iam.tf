locals {
  bucket_arn = "arn:aws:s3:::${var.bucket_name}"
}

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "image_compression" {
  name               = var.name
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "image_compression" {
  statement {
    sid       = "ReadOriginalImages"
    actions   = ["s3:GetObject", "s3:GetObjectVersion"]
    resources = ["${local.bucket_arn}/${var.config.input_prefix}*"]
    condition {
      test     = "StringEquals"
      variable = "s3:ResourceAccount"
      values   = [var.aws_account_id]
    }
  }

  statement {
    sid       = "WriteCompressedImages"
    actions   = ["s3:PutObject"]
    resources = ["${local.bucket_arn}/${var.config.output_prefix}*"]
    condition {
      test     = "StringEquals"
      variable = "s3:ResourceAccount"
      values   = [var.aws_account_id]
    }
  }

  statement {
    sid       = "WriteFunctionLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.image_compression.arn}:*"]
  }
}

resource "aws_iam_role_policy" "image_compression" {
  name   = "image-compression"
  role   = aws_iam_role.image_compression.id
  policy = data.aws_iam_policy_document.image_compression.json
}
