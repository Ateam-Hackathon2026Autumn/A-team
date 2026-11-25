# 実 AWS・リモート state を使わず、root から各リソースまでの削除設定を確認する。
mock_provider "aws" {
  mock_data "aws_s3_bucket" {
    defaults = {
      arn                         = "arn:aws:s3:::a-team-dev-frontend-123456789012-ap-northeast-1"
      bucket_regional_domain_name = "a-team-dev-frontend-123456789012-ap-northeast-1.s3.ap-northeast-1.amazonaws.com"
    }
  }
  mock_data "aws_ecr_repository" {
    defaults = {
      arn            = "arn:aws:ecr:ap-northeast-1:123456789012:repository/a-team-dev/backend"
      repository_url = "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/a-team-dev/backend"
    }
  }
  mock_data "aws_ecr_image" {
    defaults = { image_digest = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

# 削除方針と関係しない Lambda ZIP のビルドをテストの前提にしない。
override_module {
  target = module.image_compression
  outputs = {
    function_name  = "a-team-dev-image-compression-tests"
    log_group_name = "/aws/lambda/a-team-dev-image-compression-tests"
    paths          = { input = "uploads/images/", output = "uploads/compressed/" }
  }
}

variables {
  aws_account_id      = "123456789012"
  uploads_bucket_name = "a-team-dev-uploads-tests"
}

run "dev_can_delete_data_with_its_infrastructure" {
  command = plan

  assert {
    condition = output.deletion_policy == {
      alb_deletion_protection               = false
      rds_deletion_protection               = false
      db_skip_final_snapshot                = true
      frontend_force_destroy                = false
      django_secret_recovery_window_in_days = 0
      ecr_force_delete                      = false
    }
    error_message = "dev は削除保護・最終スナップショット・Secret の復旧待機を外し、フロント用 S3 と ECR は bootstrap に保持する必要があります。"
  }

  assert {
    condition = (
      output.frontend_bucket_name == "a-team-dev-frontend-123456789012-ap-northeast-1" &&
      output.application_parameter_names["AWS_STORAGE_BUCKET_NAME"] == "/a-team/dev/uploads-bucket-name"
    )
    error_message = "dev の配信バケットと設定値を prod と別の名前で作成する必要があります。"
  }
}

run "dev_can_explicitly_retain_data" {
  command = plan

  variables {
    deletion_protection                   = true
    db_skip_final_snapshot                = false
    db_final_snapshot_identifier          = "a-team-dev-final-tests"
    django_secret_recovery_window_in_days = 7
  }

  assert {
    condition = output.deletion_policy == {
      alb_deletion_protection               = true
      rds_deletion_protection               = true
      db_skip_final_snapshot                = false
      frontend_force_destroy                = false
      django_secret_recovery_window_in_days = 7
      ecr_force_delete                      = false
    }
    error_message = "明示的に指定したデータ保持設定を各モジュールへ渡す必要があります。"
  }
}

run "custom_frontend_domain_is_the_application_origin" {
  command = plan

  variables {
    frontend_domain = {
      name    = "marche.example.com"
      zone_id = "ZPUBLICEXAMPLE"
    }
  }

  assert {
    condition = (
      output.frontend_url == "https://marche.example.com" &&
      alltrue([for name in ["FRONTEND_BASE_URL", "DJANGO_CSRF_TRUSTED_ORIGINS", "DJANGO_PUBLIC_IMAGE_BASE_URL"] :
        module.application_config.values[name] == output.frontend_url
      ])
    )
    error_message = "画面の公開 URL と、Django のリンク・CSRF・画像 URL を同じドメインに揃える必要があります。"
  }
}
