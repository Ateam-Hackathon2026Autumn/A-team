mock_provider "aws" {}

override_resource {
  target = aws_ssm_parameter.application["AWS_STORAGE_BUCKET_NAME"]
  values = { arn = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/uploads-bucket-name" }
}

override_resource {
  target = aws_ssm_parameter.application["FRONTEND_BASE_URL"]
  values = { arn = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/frontend-base-url" }
}

override_resource {
  target = aws_ssm_parameter.application["DJANGO_PUBLIC_IMAGE_BASE_URL"]
  values = { arn = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/public-image-base-url" }
}

override_resource {
  target = aws_ssm_parameter.application["DJANGO_CSRF_TRUSTED_ORIGINS"]
  values = { arn = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/csrf-trusted-origins" }
}

override_resource {
  target = aws_ssm_parameter.application["DJANGO_COOKIE_SECURE"]
  values = { arn = "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/django-cookie-secure" }
}

variables {
  path_prefix         = "/a-team/dev"
  uploads_bucket_name = "a-team-uploads-tests"
  frontend_url        = "https://frontend-tests.cloudfront.net"
}

run "publish_non_secret_parameters" {
  command = apply

  assert {
    condition = output.values == {
      AWS_STORAGE_BUCKET_NAME      = "a-team-uploads-tests"
      FRONTEND_BASE_URL            = "https://frontend-tests.cloudfront.net"
      DJANGO_PUBLIC_IMAGE_BASE_URL = "https://frontend-tests.cloudfront.net"
      DJANGO_CSRF_TRUSTED_ORIGINS  = "https://frontend-tests.cloudfront.net"
      DJANGO_COOKIE_SECURE         = "true"
    }
    error_message = "アプリが読む設定の名前と値を出力し、秘密値を含めない必要があります。"
  }

  assert {
    condition = output.parameter_names == {
      AWS_STORAGE_BUCKET_NAME      = "/a-team/dev/uploads-bucket-name"
      FRONTEND_BASE_URL            = "/a-team/dev/frontend-base-url"
      DJANGO_PUBLIC_IMAGE_BASE_URL = "/a-team/dev/public-image-base-url"
      DJANGO_CSRF_TRUSTED_ORIGINS  = "/a-team/dev/csrf-trusted-origins"
      DJANGO_COOKIE_SECURE         = "/a-team/dev/django-cookie-secure"
    }
    error_message = "環境別の階層にパラメータ名を揃える必要があります。"
  }

  assert {
    condition = (
      length(aws_ssm_parameter.application) == 5 &&
      alltrue([for name, parameter in aws_ssm_parameter.application :
        parameter.type == "String" && parameter.tier == "Standard" && parameter.value == output.values[name]
      ]) &&
      length(toset(values(output.parameter_arns))) == 5 &&
      output.parameter_arns["AWS_STORAGE_BUCKET_NAME"] == "arn:aws:ssm:ap-northeast-1:123456789012:parameter/a-team/dev/uploads-bucket-name" &&
      output.revision == sha256(jsonencode(output.values))
    )
    error_message = "通常設定を Standard の String に保存し、参照 ARN と設定の revision を出力する必要があります。"
  }
}

run "frontend_change_updates_urls_and_revision" {
  command = apply

  variables {
    frontend_url = "https://new-frontend.cloudfront.net"
  }

  assert {
    condition = (
      output.values["FRONTEND_BASE_URL"] == "https://new-frontend.cloudfront.net" &&
      output.values["DJANGO_PUBLIC_IMAGE_BASE_URL"] == "https://new-frontend.cloudfront.net" &&
      output.values["DJANGO_CSRF_TRUSTED_ORIGINS"] == "https://new-frontend.cloudfront.net" &&
      output.values["AWS_STORAGE_BUCKET_NAME"] == "a-team-uploads-tests" &&
      output.revision != run.publish_non_secret_parameters.revision &&
      output.parameter_names == run.publish_non_secret_parameters.parameter_names
    )
    error_message = "CloudFront の変更時は公開 URL と CSRF の値・revision が更新され、パラメータ名は安定している必要があります。"
  }
}

run "reject_plain_http_frontend" {
  command = plan

  variables {
    frontend_url = "http://frontend-tests.cloudfront.net"
  }

  expect_failures = [var.frontend_url]
}

run "reject_path_in_csrf_origin" {
  command = plan

  variables {
    frontend_url = "https://frontend-tests.cloudfront.net/path/"
  }

  expect_failures = [var.frontend_url]
}
