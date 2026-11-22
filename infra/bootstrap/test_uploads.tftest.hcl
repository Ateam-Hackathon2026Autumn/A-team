mock_provider "aws" {
  override_during = plan

  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }

  override_resource {
    target = aws_s3_bucket.test_uploads
    values = { arn = "arn:aws:s3:::a-team-test-uploads-123456789012-ap-northeast-1" }
  }
}

variables {
  aws_account_id      = "123456789012"
  state_bucket_name   = "a-team-state-tests"
  uploads_bucket_name = "a-team-uploads-tests"
}

run "test_uploads_are_limited_to_images" {
  command = plan

  assert {
    condition = (
      aws_s3_bucket.test_uploads.bucket == "a-team-test-uploads-123456789012-ap-northeast-1" &&
      aws_s3_bucket_public_access_block.uploads.block_public_policy &&
      aws_s3_bucket_public_access_block.test_uploads.block_public_acls &&
      aws_s3_bucket_public_access_block.test_uploads.ignore_public_acls
    )
    error_message = "検証用バケットを分け、ACL による公開と既存アップロード用バケットの公開をブロックします。"
  }

  assert {
    condition = alltrue([for statement in data.aws_iam_policy_document.test_uploads_bucket.statement :
      statement.effect == "Deny" || (
        toset(statement.actions) == toset(["s3:GetObject"]) &&
        toset(statement.resources) == toset(["${aws_s3_bucket.test_uploads.arn}/images/*"])
      )
      ]) && (
      toset(one(data.aws_iam_policy_document.test_uploads_writer.statement).actions) == toset(["s3:GetObject", "s3:PutObject", "s3:AbortMultipartUpload", "s3:DeleteObject"]) &&
      toset(one(data.aws_iam_policy_document.test_uploads_writer.statement).resources) == toset(["${aws_s3_bucket.test_uploads.arn}/images/*"])
    )
    error_message = "公開は検証用 images/ の GET のみとし、IAM の書き込み・削除権限も同じ範囲に限定します。"
  }
}
