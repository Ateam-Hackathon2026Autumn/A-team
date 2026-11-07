output "repository" {
  description = "イメージの保存先 URL と、ECS 実行ロールの権限設定に使うリポジトリ ARN。"
  value = {
    url = aws_ecr_repository.backend.repository_url
    arn = aws_ecr_repository.backend.arn
  }
}
