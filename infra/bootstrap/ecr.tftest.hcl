# plan のみ。bootstrap の prevent_destroy と AWS 実リソースには触れない。
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

run "persistent_dev_ecr" {
  command = plan

  assert {
    condition = (
      toset(keys(output.backend_ecr_repositories)) == toset(["dev"]) &&
      output.backend_ecr_repositories["dev"].name == "a-team-dev/backend" &&
      !module.ecr["dev"].force_delete &&
      module.ecr["dev"].image_tag_mutability == "MUTABLE"
    )
    error_message = "既存と同じ名前の dev ECR を bootstrap が保持し、強制削除を無効・同じタグの上書きを有効にする必要があります。"
  }
}

run "add_separate_prod_ecr" {
  command = plan
  variables { ecr_environments = ["dev", "prod"] }

  assert {
    condition = (
      output.backend_ecr_repositories["dev"].name == "a-team-dev/backend" &&
      output.backend_ecr_repositories["prod"].name == "a-team-prod/backend" &&
      !module.ecr["prod"].force_delete &&
      module.ecr["dev"].image_tag_mutability == "MUTABLE" &&
      module.ecr["prod"].image_tag_mutability == "IMMUTABLE"
    )
    error_message = "prod は dev と別の名前で ECR を保持し、prod のタグは上書きを禁止する必要があります。"
  }
}
