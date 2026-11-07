# バケット自体は bootstrap が管理します。dev はアプリのアクセス権だけを管理します。
locals {
  uploads_bucket_arn = "arn:aws:s3:::${var.uploads_bucket_name}"
  # uploads/ の外へ画像の保存先を変更した場合も、必要な prefix だけ追加します。
  uploads_prefixes = distinct(concat(["uploads/"], [
    for prefix in [var.image_prefixes.input, var.image_prefixes.output] : prefix
    if !startswith(prefix, "uploads/")
  ]))
}

data "aws_iam_policy_document" "ecs_uploads" {
  statement {
    sid       = "ListUploads"
    actions   = ["s3:ListBucket"]
    resources = [local.uploads_bucket_arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = flatten([for prefix in local.uploads_prefixes : [prefix, "${prefix}*"]])
    }

    condition {
      test     = "StringEquals"
      variable = "s3:ResourceAccount"
      values   = [var.aws_account_id]
    }
  }

  statement {
    sid = "ReadAndWriteUploads"
    actions = [
      "s3:GetObject",
      "s3:PutObject",
      "s3:AbortMultipartUpload",
      "s3:ListMultipartUploadParts",
    ]
    resources = [for prefix in local.uploads_prefixes : "${local.uploads_bucket_arn}/${prefix}*"]

    condition {
      test     = "StringEquals"
      variable = "s3:ResourceAccount"
      values   = [var.aws_account_id]
    }
  }
}

resource "aws_iam_role_policy" "ecs_uploads" {
  name   = "application-uploads"
  role   = aws_iam_role.ecs_task.id
  policy = data.aws_iam_policy_document.ecs_uploads.json
}
