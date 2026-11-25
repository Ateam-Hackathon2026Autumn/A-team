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
      arn            = "arn:aws:cloudfront::123456789012:distribution/EFRONTENDTEST"
      domain_name    = "frontend-tests.cloudfront.net"
      hosted_zone_id = "Z2FDTNDATAQYW2"
    }
  }

  mock_resource "aws_acm_certificate" {
    defaults = {
      arn = "arn:aws:acm:us-east-1:123456789012:certificate/11111111-1111-1111-1111-111111111111"
      domain_validation_options = [{
        domain_name           = "marche.example.com"
        resource_record_name  = "_validation.marche.example.com"
        resource_record_type  = "CNAME"
        resource_record_value = "_target.acm-validations.aws."
      }]
    }
  }

  mock_resource "aws_s3_access_point" {
    defaults = {
      arn    = "arn:aws:s3:ap-northeast-1:123456789012:accesspoint/a-team-dev-public-images"
      alias  = "a-team-dev-public-images-test-s3alias"
      region = "ap-northeast-1"
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

  assert {
    condition = (
      output.url == "https://frontend-tests.cloudfront.net" &&
      length(aws_cloudfront_distribution.site.aliases) == 0 &&
      one(aws_cloudfront_distribution.site.viewer_certificate).cloudfront_default_certificate &&
      length(aws_acm_certificate.frontend) == 0 && length(aws_route53_record.frontend) == 0
    )
    error_message = "独自ドメイン未指定時に CloudFront の標準 HTTPS URL を返す必要があります。"
  }
}

run "custom_domain_uses_validated_certificate_and_aliases" {
  command = apply

  variables {
    custom_domain = {
      name    = "marche.example.com"
      zone_id = "ZPUBLICEXAMPLE"
    }
  }

  assert {
    condition = (
      one(aws_acm_certificate.frontend).region == "us-east-1" &&
      one(aws_acm_certificate.frontend).validation_method == "DNS" &&
      one(aws_route53_record.certificate_validation).type == "CNAME" &&
      one(aws_route53_record.certificate_validation).zone_id == var.custom_domain.zone_id &&
      one(aws_acm_certificate_validation.frontend).region == "us-east-1" &&
      toset(one(aws_acm_certificate_validation.frontend).validation_record_fqdns) == toset([one(aws_route53_record.certificate_validation).fqdn]) &&
      toset(aws_cloudfront_distribution.site.aliases) == toset([var.custom_domain.name]) &&
      !one(aws_cloudfront_distribution.site.viewer_certificate).cloudfront_default_certificate &&
      one(aws_cloudfront_distribution.site.viewer_certificate).acm_certificate_arn == one(aws_acm_certificate_validation.frontend).certificate_arn &&
      one(aws_cloudfront_distribution.site.viewer_certificate).ssl_support_method == "sni-only"
    )
    error_message = "us-east-1 の ACM 証明書を Route 53 で DNS 検証し、CloudFront に設定する必要があります。"
  }

  assert {
    condition = (
      output.url == "https://marche.example.com" &&
      toset(keys(aws_route53_record.frontend)) == toset(["A", "AAAA"]) &&
      alltrue([for record in aws_route53_record.frontend :
        record.zone_id == var.custom_domain.zone_id && record.name == var.custom_domain.name &&
        one(record.alias).name == aws_cloudfront_distribution.site.domain_name &&
        one(record.alias).zone_id == aws_cloudfront_distribution.site.hosted_zone_id &&
        !one(record.alias).evaluate_target_health
      ])
    )
    error_message = "公開 URL を独自ドメインにし、IPv4・IPv6 を同じ CloudFront に転送する必要があります。"
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

run "images_use_private_bucket_access_point" {
  command = apply

  variables {
    uploads_bucket_name = "a-team-dev-uploads-tests"
  }

  assert {
    condition = (
      aws_s3_access_point.images[0].bucket == var.uploads_bucket_name &&
      aws_s3_access_point.images[0].name == "a-team-dev-public-images" &&
      aws_s3_access_point.images[0].public_access_block_configuration[0].block_public_policy &&
      one([for origin in aws_cloudfront_distribution.site.origin : origin.domain_name if origin.origin_id == "uploads-images-s3"]) == "a-team-dev-public-images-test-s3alias.s3.ap-northeast-1.amazonaws.com" &&
      one([for origin in aws_cloudfront_distribution.site.origin : origin.origin_access_control_id if origin.origin_id == "uploads-images-s3"]) == aws_cloudfront_origin_access_control.site.id
    )
    error_message = "アップロード用 S3 のアクセスポイントを、署名付きの画像配信元にする必要があります。"
  }

  assert {
    condition = (
      one(aws_cloudfront_distribution.site.ordered_cache_behavior).path_pattern == "/images/*" &&
      one(aws_cloudfront_distribution.site.ordered_cache_behavior).target_origin_id == "uploads-images-s3" &&
      toset(one(aws_cloudfront_distribution.site.ordered_cache_behavior).allowed_methods) == toset(["GET", "HEAD"]) &&
      length(one(aws_cloudfront_distribution.site.ordered_cache_behavior).function_association) == 0 &&
      one(jsondecode(aws_s3control_access_point_policy.images[0].policy).Statement).Resource == "${aws_s3_access_point.images[0].arn}/object/images/*" &&
      one(jsondecode(aws_s3control_access_point_policy.images[0].policy).Statement).Action == "s3:GetObject" &&
      one(jsondecode(aws_s3control_access_point_policy.images[0].policy).Statement).Condition.StringEquals["AWS:SourceArn"] == aws_cloudfront_distribution.site.arn
    )
    error_message = "この CloudFront だけに images/ を許可し、画像リクエストは読み取り専用で転送する必要があります。"
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
