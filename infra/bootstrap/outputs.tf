output "state_bucket_name" {
  description = "各 root module の backend.s3.tfbackend に指定する state 用バケット名。"
  value       = aws_s3_bucket.terraform_state.id
}

output "state_bucket_arn" {
  description = "backend へのアクセス権限を設定する際に使う S3 バケット ARN。"
  value       = aws_s3_bucket.terraform_state.arn
}

output "uploads_bucket_name" {
  description = "画像・その他ファイルを保存する S3 バケット名。state 用とは別のバケットです。"
  value       = aws_s3_bucket.uploads.id
}

output "uploads_bucket_arn" {
  description = "アプリのアクセス権限や配信設定に使用する画像・ファイル用 S3 バケット ARN。"
  value       = aws_s3_bucket.uploads.arn
}

output "upload_paths" {
  description = "画像とその他ファイルのアップロード先 S3 URI。"
  value = {
    images = "s3://${aws_s3_bucket.uploads.id}/uploads/images/"
    files  = "s3://${aws_s3_bucket.uploads.id}/uploads/files/"
  }
}

output "uploads_access_policy_json" {
  description = "画像用バケットの uploads/ だけを読み書きできる IAM ポリシーの雛形。アプリのロールへの付与は別途行います。"
  value       = data.aws_iam_policy_document.uploads.json
}
