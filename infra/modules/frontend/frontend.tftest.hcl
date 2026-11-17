# AWS の作成・変更を行わず、配信と認証情報の転送に関する設定を確認する。
mock_provider "aws" {
  mock_data "aws_s3_bucket" {
    defaults = {
      arn                         = "arn:aws:s3:::a-team-dev-frontend-tests"
      bucket_regional_domain_name = "a-team-dev-frontend-tests.s3.ap-northeast-1.amazonaws.com"
    }
  }

  mock_resource "aws_cloudfront_distribution" {
    defaults = {
      arn         = "arn:aws:cloudfront::123456789012:distribution/EFRONTENDTEST"
      domain_name = "frontend-tests.cloudfront.net"
    }
  }

  mock_resource "aws_cloudfront_cache_policy" {
    defaults = { id = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa" }
  }

  mock_resource "aws_cloudfront_origin_request_policy" {
    defaults = { id = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb" }
  }

  mock_resource "aws_cloudfront_function" {
    defaults = { arn = "arn:aws:cloudfront::123456789012:function/a-team-dev-frontend-spa" }
  }
}

variables {
  name        = "a-team-dev"
  bucket_name = "a-team-dev-frontend-tests"
}

run "private_static_site" {
  command = apply

  assert {
    condition = (
      data.aws_s3_bucket.site.bucket == var.bucket_name &&
      aws_s3_bucket_policy.site.bucket == var.bucket_name &&
      output.bucket_name == var.bucket_name
    )
    error_message = "bootstrap の既存 S3 と、そのバケットだけの配信ポリシーを参照する必要があります。"
  }

  assert {
    condition = (
      jsondecode(aws_s3_bucket_policy.site.policy).Statement[0].Principal.Service == "cloudfront.amazonaws.com" &&
      jsondecode(aws_s3_bucket_policy.site.policy).Statement[0].Action == "s3:GetObject" &&
      jsondecode(aws_s3_bucket_policy.site.policy).Statement[0].Condition.StringEquals["AWS:SourceArn"] == aws_cloudfront_distribution.site.arn &&
      jsondecode(aws_s3_bucket_policy.site.policy).Statement[1].Effect == "Deny" &&
      jsondecode(aws_s3_bucket_policy.site.policy).Statement[1].Condition.Bool["aws:SecureTransport"] == "false"
    )
    error_message = "指定した CloudFront だけに読み取りを許可し、非 TLS 通信を拒否する必要があります。"
  }

  assert {
    condition = (
      aws_cloudfront_origin_access_control.site.signing_behavior == "always" &&
      aws_cloudfront_origin_access_control.site.signing_protocol == "sigv4" &&
      one(aws_cloudfront_distribution.site.origin).domain_name == data.aws_s3_bucket.site.bucket_regional_domain_name &&
      one(aws_cloudfront_distribution.site.origin).origin_access_control_id == aws_cloudfront_origin_access_control.site.id
    )
    error_message = "既存 S3 のリージョン別 endpoint を OAC の署名付き origin とする必要があります。"
  }

  assert {
    condition = (
      length(aws_cloudfront_distribution.site.origin) == 1 &&
      length(aws_cloudfront_distribution.site.ordered_cache_behavior) == 0 &&
      aws_cloudfront_distribution.site.default_cache_behavior[0].viewer_protocol_policy == "redirect-to-https" &&
      toset(aws_cloudfront_distribution.site.default_cache_behavior[0].allowed_methods) == toset(["GET", "HEAD"]) &&
      length(aws_cloudfront_distribution.site.custom_error_response) == 0 &&
      aws_cloudfront_cache_policy.site.min_ttl == 0 &&
      !output.force_destroy
    )
    error_message = "静的配信は HTTPS・読み取り専用とし、エラー全体の HTML 化や強制キャッシュを行わない必要があります。"
  }
}

run "api_requests_keep_credentials_and_methods" {
  command = apply

  variables {
    api_origin = {
      domain_name     = "backend-tests.ap-northeast-1.elb.amazonaws.com"
      protocol_policy = "http-only"
    }
  }

  assert {
    condition = (
      length(aws_cloudfront_distribution.site.origin) == 2 &&
      toset([for behavior in aws_cloudfront_distribution.site.ordered_cache_behavior : behavior.path_pattern]) == toset(["/api", "/api/*"]) &&
      alltrue([for behavior in aws_cloudfront_distribution.site.ordered_cache_behavior :
        behavior.target_origin_id == "backend-alb" &&
        behavior.cache_policy_id == "4135ea2d-6df8-44a3-9df3-4b5a84be39ad" &&
        behavior.origin_request_policy_id == aws_cloudfront_origin_request_policy.api[0].id &&
        toset(behavior.allowed_methods) == toset(["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]) &&
        length(behavior.function_association) == 0
      ])
    )
    error_message = "API は全メソッドをバックへ転送し、キャッシュと SPA 書き換えを適用しない必要があります。"
  }

  assert {
    condition = (
      aws_cloudfront_origin_request_policy.api[0].cookies_config[0].cookie_behavior == "all" &&
      aws_cloudfront_origin_request_policy.api[0].query_strings_config[0].query_string_behavior == "all" &&
      aws_cloudfront_origin_request_policy.api[0].headers_config[0].header_behavior == "allExcept" &&
      toset(aws_cloudfront_origin_request_policy.api[0].headers_config[0].headers[0].items) == toset(["Host"])
    )
    error_message = "Cookie・CSRF 等のヘッダー・クエリを転送し、Host は接続先に合わせる必要があります。"
  }
}

run "https_origin_uses_configured_domain" {
  command = apply

  variables {
    api_origin = {
      domain_name     = "api-origin.example.com"
      protocol_policy = "https-only"
    }
  }

  assert {
    condition = length([for origin in aws_cloudfront_distribution.site.origin : origin if origin.origin_id == "backend-alb"]) == 1 && alltrue([for origin in aws_cloudfront_distribution.site.origin :
      origin.origin_id != "backend-alb" ? true : (
        origin.domain_name == "api-origin.example.com" &&
        origin.custom_origin_config[0].origin_protocol_policy == "https-only" &&
        toset(origin.custom_origin_config[0].origin_ssl_protocols) == toset(["TLSv1.2"])
      )
    ])
    error_message = "HTTPS 接続先の DNS 名とプロトコルを ALB 証明書に合わせる必要があります。"
  }
}

run "reject_origin_urls_with_a_scheme" {
  command = plan

  variables {
    api_origin = {
      domain_name     = "https://api-origin.example.com/path"
      protocol_policy = "https-only"
    }
  }

  expect_failures = [var.api_origin]
}
