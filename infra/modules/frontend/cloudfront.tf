locals {
  site_origin_id = "frontend-s3"
  api_origin_id  = "backend-alb"
  # AWS 管理ポリシー CachingDisabled。API の本文・認証状態をキャッシュしない。
  api_cache_policy_id = "4135ea2d-6df8-44a3-9df3-4b5a84be39ad"
}

resource "aws_cloudfront_origin_access_control" "site" {
  name                              = "${var.name}-frontend"
  description                       = "Private frontend S3 access"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_function" "spa" {
  name    = "${var.name}-frontend-spa"
  runtime = "cloudfront-js-2.0"
  comment = "Rewrite extensionless UI routes to index.html"
  publish = true
  code    = file("${path.module}/spa-rewrite.js")
}

resource "aws_cloudfront_cache_policy" "site" {
  name        = "${var.name}-frontend"
  comment     = "Respect asset Cache-Control without forcing a minimum TTL"
  min_ttl     = 0
  default_ttl = 0
  max_ttl     = 31536000

  parameters_in_cache_key_and_forwarded_to_origin {
    enable_accept_encoding_brotli = true
    enable_accept_encoding_gzip   = true
    cookies_config { cookie_behavior = "none" }
    headers_config { header_behavior = "none" }
    query_strings_config { query_string_behavior = "none" }
  }
}

resource "aws_cloudfront_origin_request_policy" "api" {
  count = var.api_origin == null ? 0 : 1

  name    = "${var.name}-frontend-api"
  comment = "Forward API cookies, query strings and headers; use the origin Host"
  cookies_config { cookie_behavior = "all" }
  query_strings_config { query_string_behavior = "all" }

  # Host は ALB 接続先の DNS 名にする。公開 origin の CSRF 信頼設定は Django 側で行う。
  headers_config {
    header_behavior = "allExcept"
    headers { items = ["Host"] }
  }
}

resource "aws_cloudfront_distribution" "site" {
  enabled             = true
  is_ipv6_enabled     = true
  comment             = "${var.name} frontend and API entry point"
  default_root_object = "index.html"
  http_version        = "http2and3"
  price_class         = "PriceClass_200"
  wait_for_deployment = true
  retain_on_delete    = false

  origin {
    origin_id                = local.site_origin_id
    domain_name              = data.aws_s3_bucket.site.bucket_regional_domain_name
    origin_access_control_id = aws_cloudfront_origin_access_control.site.id
  }

  dynamic "origin" {
    for_each = var.api_origin == null ? [] : [var.api_origin]
    content {
      origin_id   = local.api_origin_id
      domain_name = origin.value.domain_name

      custom_origin_config {
        http_port              = 80
        https_port             = 443
        origin_protocol_policy = origin.value.protocol_policy
        origin_ssl_protocols   = ["TLSv1.2"]
      }
    }
  }

  default_cache_behavior {
    target_origin_id       = local.site_origin_id
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    cache_policy_id        = aws_cloudfront_cache_policy.site.id

    function_association {
      event_type   = "viewer-request"
      function_arn = aws_cloudfront_function.spa.arn
    }
  }

  dynamic "ordered_cache_behavior" {
    # /api 自体もバックへ渡し、SPA に誤って書き換えられることを防ぐ。
    for_each = var.api_origin == null ? [] : ["/api", "/api/*"]
    content {
      path_pattern             = ordered_cache_behavior.value
      target_origin_id         = local.api_origin_id
      viewer_protocol_policy   = "redirect-to-https"
      allowed_methods          = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
      cached_methods           = ["GET", "HEAD"]
      compress                 = true
      cache_policy_id          = local.api_cache_policy_id
      origin_request_policy_id = aws_cloudfront_origin_request_policy.api[0].id
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

}
