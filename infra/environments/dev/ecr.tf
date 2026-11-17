# イメージは bootstrap の常駐 ECR に、dev/prod の apply より先に push する。
data "aws_ecr_repository" "backend" {
  name = "${local.name}/backend"
}

# タグが存在しなければ plan 時点で失敗させ、同じ digest をサービスと migration で使う。
data "aws_ecr_image" "backend" {
  repository_name = data.aws_ecr_repository.backend.name
  image_tag       = var.image_tag
}

# 旧 dev/prod state の ECR は AWS 上で削除せず、bootstrap へ import して引き継ぐ。
removed {
  from = module.ecr
  lifecycle { destroy = false }
}

# モジュール化前の state にも対応する。
removed {
  from = aws_ecr_repository.backend
  lifecycle { destroy = false }
}
removed {
  from = aws_ecr_lifecycle_policy.backend
  lifecycle { destroy = false }
}
