# prod の削除保護が、root の既定値から各リソースまで渡ることを確認する。
mock_provider "aws" {
  mock_data "aws_s3_bucket" {
    defaults = {
      arn                         = "arn:aws:s3:::a-team-prod-frontend-123456789012-ap-northeast-1"
      bucket_regional_domain_name = "a-team-prod-frontend-123456789012-ap-northeast-1.s3.ap-northeast-1.amazonaws.com"
    }
  }
  mock_data "aws_ecr_repository" {
    defaults = {
      arn            = "arn:aws:ecr:ap-northeast-1:123456789012:repository/a-team-prod/backend"
      repository_url = "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/a-team-prod/backend"
    }
  }
  mock_data "aws_ecr_image" {
    defaults = { image_digest = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

override_module {
  target = module.image_compression
  outputs = {
    function_name  = "a-team-prod-image-compression-tests"
    log_group_name = "/aws/lambda/a-team-prod-image-compression-tests"
    paths          = { input = "uploads/images/", output = "uploads/compressed/" }
  }
}

variables {
  aws_account_id               = "123456789012"
  uploads_bucket_name          = "a-team-prod-uploads-tests"
  db_final_snapshot_identifier = "a-team-prod-final-tests"
}

run "prod_retains_data_and_enables_deletion_protection" {
  command = plan

  assert {
    condition = output.deletion_policy == {
      alb_deletion_protection               = true
      rds_deletion_protection               = true
      db_skip_final_snapshot                = false
      frontend_force_destroy                = false
      django_secret_recovery_window_in_days = 30
      ecr_force_delete                      = false
    }
    error_message = "prod は ALB・RDS の削除保護、DB の最終スナップショット、S3・ECR の保持、Secret の復旧期間を有効にする必要があります。"
  }

  assert {
    condition = (
      output.frontend_bucket_name == "a-team-prod-frontend-123456789012-ap-northeast-1" &&
      output.application_parameter_names["AWS_STORAGE_BUCKET_NAME"] == "/a-team/prod/uploads-bucket-name"
    )
    error_message = "prod の配信バケットと設定値を dev と別の名前で作成する必要があります。"
  }
}
