module "image_compression" {
  source = "../../modules/image_compression"

  name           = "${local.name}-image-compression"
  aws_account_id = var.aws_account_id
  bucket_name    = var.uploads_bucket_name
  config         = var.image_compression
  package_path   = var.image_compression_package_path != null ? abspath(var.image_compression_package_path) : abspath("${path.module}/../../lambda/image_compression/dist/image_compression.zip")
}

variable "image_compression" {
  description = "画像圧縮の設定。保存先 prefix・形式・品質・最大寸法など、変更する項目だけ terraform.tfvars で指定します。"
  type = object({
    input_prefix         = optional(string, "uploads/images/")
    output_prefix        = optional(string, "uploads/compressed/")
    output_format        = optional(string, "webp")
    quality              = optional(number, 80)
    max_width            = optional(number, 1920)
    max_height           = optional(number, 1920)
    max_input_bytes      = optional(number, 20 * 1024 * 1024)
    max_input_pixels     = optional(number, 25000000)
    memory_size          = optional(number, 1024)
    timeout              = optional(number, 60)
    reserved_concurrency = optional(number, 5)
  })
  default  = {}
  nullable = false
}

variable "image_compression_package_path" {
  description = "ビルド済み Lambda ZIP のパス。null は infra/lambda/image_compression/dist/image_compression.zip。相対パスは Terraform の実行ディレクトリから解釈します。"
  type        = string
  default     = null
}

output "image_compression_function_name" {
  description = "画像圧縮 Lambda の関数名。"
  value       = module.image_compression.function_name
}

output "image_compression_log_group_name" {
  description = "画像圧縮の結果やエラーを確認するロググループ。"
  value       = module.image_compression.log_group_name
}

output "image_compression_paths" {
  description = "元画像と圧縮画像の保存先。"
  value       = module.image_compression.paths
}
