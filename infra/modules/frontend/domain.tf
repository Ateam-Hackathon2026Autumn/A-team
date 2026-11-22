resource "aws_acm_certificate" "frontend" {
  count = var.custom_domain == null ? 0 : 1

  # CloudFront の閲覧者向け証明書は米国東部（バージニア北部）に作成する。
  region            = "us-east-1"
  domain_name       = var.custom_domain.name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "certificate_validation" {
  count = length(aws_acm_certificate.frontend)

  zone_id = var.custom_domain.zone_id
  name    = one(aws_acm_certificate.frontend[count.index].domain_validation_options).resource_record_name
  type    = one(aws_acm_certificate.frontend[count.index].domain_validation_options).resource_record_type
  records = [one(aws_acm_certificate.frontend[count.index].domain_validation_options).resource_record_value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "frontend" {
  count = length(aws_acm_certificate.frontend)

  region                  = aws_acm_certificate.frontend[count.index].region
  certificate_arn         = aws_acm_certificate.frontend[count.index].arn
  validation_record_fqdns = [aws_route53_record.certificate_validation[count.index].fqdn]
}

resource "aws_route53_record" "frontend" {
  for_each = var.custom_domain == null ? toset([]) : toset(["A", "AAAA"])

  zone_id = var.custom_domain.zone_id
  name    = var.custom_domain.name
  type    = each.key

  alias {
    name                   = aws_cloudfront_distribution.site.domain_name
    zone_id                = aws_cloudfront_distribution.site.hosted_zone_id
    evaluate_target_health = false
  }
}
