# dev / prod の作り直しとは独立してイメージを保持する。
# 既存の ${project_name}-dev/backend と同じ名前を使うため、作成済みなら先に import する。
module "ecr" {
  for_each = var.ecr_environments
  source   = "../modules/ecr"

  name                 = "${var.project_name}-${each.key}"
  image_tag_mutability = each.key == "dev" ? "MUTABLE" : "IMMUTABLE"
}

variable "ecr_environments" {
  description = "常駐 ECR を用意する環境。prod を追加する場合は dev を残して指定します。"
  type        = set(string)
  default     = ["dev"]

  validation {
    condition     = length(var.ecr_environments) > 0 && alltrue([for environment in var.ecr_environments : contains(["dev", "prod"], environment)])
    error_message = "ecr_environments は dev / prod から1つ以上指定してください。"
  }
}

output "backend_ecr_repositories" {
  description = "環境名からバックエンドの ECR 名・URL・ARN を引ける map。ビルド・push に使います。"
  value       = { for environment, repository in module.ecr : environment => repository.repository }
}
