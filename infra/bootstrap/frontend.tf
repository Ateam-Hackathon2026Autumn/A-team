module "frontend_storage" {
  for_each = var.frontend_environments
  source   = "../modules/frontend_storage"

  bucket_name = "${var.project_name}-${each.key}-frontend-${var.aws_account_id}-${var.aws_region}"
}

variable "frontend_environments" {
  description = "常駐フロント用 S3 を用意する環境。prod 追加時は dev も残します。"
  type        = set(string)
  default     = ["dev"]

  validation {
    condition     = length(var.frontend_environments) > 0 && alltrue([for environment in var.frontend_environments : contains(["dev", "prod"], environment)])
    error_message = "frontend_environments は dev / prod から1つ以上指定してください。"
  }
}

output "frontend_deployments" {
  description = "環境別のフロント配置先。CloudFront 作成前でも Bash から取得できます。秘密値は含みません。"
  value = {
    for environment, storage in module.frontend_storage : environment => {
      environment    = environment
      aws_account_id = var.aws_account_id
      aws_region     = var.aws_region
      bucket_name    = storage.bucket_name
    }
  }
}
