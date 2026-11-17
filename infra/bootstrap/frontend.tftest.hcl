# plan のみ。常駐 S3 は実 AWS・テスト上とも destroy しない。
mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

variables {
  aws_account_id      = "123456789012"
  state_bucket_name   = "a-team-state-tests"
  uploads_bucket_name = "a-team-uploads-tests"
}

run "frontend_can_be_uploaded_before_dev_exists" {
  command = plan

  assert {
    condition = (
      toset(keys(output.frontend_deployments)) == toset(["dev"]) &&
      output.frontend_deployments["dev"].environment == "dev" &&
      output.frontend_deployments["dev"].aws_account_id == "123456789012" &&
      output.frontend_deployments["dev"].aws_region == "ap-northeast-1" &&
      output.frontend_deployments["dev"].bucket_name == "a-team-dev-frontend-123456789012-ap-northeast-1"
    )
    error_message = "CloudFront / dev の output に依存せず、従来と同じ名前の配置先を出力する必要があります。"
  }
}

run "frontend_storage_is_separate_for_prod" {
  command = plan
  variables { frontend_environments = ["dev", "prod"] }

  assert {
    condition = (
      output.frontend_deployments["dev"].bucket_name != output.frontend_deployments["prod"].bucket_name &&
      output.frontend_deployments["prod"].bucket_name == "a-team-prod-frontend-123456789012-ap-northeast-1"
    )
    error_message = "dev / prod のフロント成果物を別バケットで保持する必要があります。"
  }
}
