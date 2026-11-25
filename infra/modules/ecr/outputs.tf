output "repository" {
  description = "イメージの保存先 URL と、ECS 実行ロールの権限設定に使うリポジトリ ARN。"
  value = {
    name = aws_ecr_repository.backend.name
    url  = aws_ecr_repository.backend.repository_url
    arn  = aws_ecr_repository.backend.arn
  }
}

output "force_delete" {
  description = "リポジトリ削除時にイメージも削除するか。"
  value       = aws_ecr_repository.backend.force_delete
}

output "image_tag_mutability" {
  description = "同じイメージタグの上書きを許可するか。"
  value       = aws_ecr_repository.backend.image_tag_mutability
}
