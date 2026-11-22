# plan のみ。常駐 S3 は実 AWS・テスト上とも destroy しない。
mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{\"Version\":\"2012-10-17\",\"Statement\":[]}" }
  }
}

override_resource {
  target          = aws_s3_bucket.uploads
  override_during = plan
  values          = { arn = "arn:aws:s3:::a-team-uploads-tests" }
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

  assert {
    condition = anytrue([for statement in data.aws_iam_policy_document.uploads_bucket.statement :
      statement.sid == "DelegatePublicImageReadsToAccessPoints" &&
      toset(statement.actions) == toset(["s3:GetObject"]) &&
      toset(statement.resources) == toset(["arn:aws:s3:::a-team-uploads-tests/images/*"]) &&
      anytrue([for principal in statement.principals :
        principal.type == "Service" && toset(principal.identifiers) == toset(["cloudfront.amazonaws.com"])
      ]) &&
      anytrue([for condition in statement.condition :
        condition.test == "ArnEquals" && condition.variable == "s3:DataAccessPointArn" &&
        toset(condition.values) == toset([
          "arn:aws:s3:ap-northeast-1:123456789012:accesspoint/a-team-dev-public-images",
          "arn:aws:s3:ap-northeast-1:123456789012:accesspoint/a-team-prod-public-images"
        ])
      ])
    ])
    error_message = "既知の画像配信用アクセスポイントに、images/ の読み取りだけを委譲する必要があります。"
  }
}
