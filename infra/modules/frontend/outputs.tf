output "bucket_name" {
  description = "ビルド済み frontend/dist を配置するフロント用バケット名。"
  value       = data.aws_s3_bucket.site.bucket
}

output "url" {
  description = "画面と API の共通入口になる CloudFront の HTTPS URL。"
  value       = "https://${var.custom_domain == null ? aws_cloudfront_distribution.site.domain_name : var.custom_domain.name}"
  depends_on  = [aws_route53_record.frontend]
}

output "distribution_id" {
  description = "キャッシュ更新等で使う CloudFront Distribution ID。"
  value       = aws_cloudfront_distribution.site.id
}

output "distribution_arn" {
  description = "CloudFront Distribution ARN。フロント用 S3 の OAC 許可にも使用します。"
  value       = aws_cloudfront_distribution.site.arn
}

output "force_destroy" {
  description = "S3 本体は bootstrap で保持するため、このモジュールから強制削除しません。"
  value       = false
}
