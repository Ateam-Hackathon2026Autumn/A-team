# S3 コンソールからも保存先が分かるよう、空のフォルダオブジェクトを作成します。
# 画像・ファイルの実データは Terraform では管理せず、CLI やアプリからアップロードします。
resource "aws_s3_object" "upload_folders" {
  for_each = toset(["uploads/images/", "uploads/files/"])

  bucket                 = aws_s3_bucket.uploads.id
  key                    = each.value
  content                = ""
  server_side_encryption = "AES256"

  depends_on = [
    aws_s3_bucket_versioning.uploads,
    aws_s3_bucket_server_side_encryption_configuration.uploads,
    aws_s3_bucket_public_access_block.uploads,
    aws_s3_bucket_ownership_controls.uploads,
    aws_s3_bucket_policy.uploads,
  ]
}

# アプリの IAM ロールに後から付与する権限の雛形。ここでは IAM の作成・付与は行いません。
# 画像用バケットの uploads/ 配下に限定し、state 用バケットへの権限は含めません。
data "aws_iam_policy_document" "uploads" {
  statement {
    sid       = "ListUploads"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.uploads.arn]

    condition {
      test     = "StringLike"
      variable = "s3:prefix"
      values   = ["uploads/", "uploads/*"]
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
    resources = ["${aws_s3_bucket.uploads.arn}/uploads/*"]
  }
}
