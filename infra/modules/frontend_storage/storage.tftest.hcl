mock_provider "aws" {}

variables { bucket_name = "a-team-dev-frontend-tests" }

run "private_encrypted_retained_storage" {
  command = plan

  assert {
    condition = (
      aws_s3_bucket.site.bucket == var.bucket_name &&
      !aws_s3_bucket.site.force_destroy &&
      aws_s3_bucket_public_access_block.site.block_public_acls &&
      aws_s3_bucket_public_access_block.site.block_public_policy &&
      aws_s3_bucket_public_access_block.site.ignore_public_acls &&
      aws_s3_bucket_public_access_block.site.restrict_public_buckets &&
      aws_s3_bucket_ownership_controls.site.rule[0].object_ownership == "BucketOwnerEnforced" &&
      one(aws_s3_bucket_server_side_encryption_configuration.site.rule).apply_server_side_encryption_by_default[0].sse_algorithm == "AES256"
    )
    error_message = "保持する S3 は強制削除を無効にし、非公開・所有権強制・AES256 暗号化を有効にする必要があります。"
  }
}
