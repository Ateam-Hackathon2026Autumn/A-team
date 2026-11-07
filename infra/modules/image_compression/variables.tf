variable "name" {
  description = "画像圧縮 Lambda と IAM ロールの名前。"
  type        = string
}

variable "aws_account_id" {
  description = "画像用バケットを所有する AWS アカウント ID。"
  type        = string
}

variable "bucket_name" {
  description = "bootstrap で作成済みの画像用 S3 バケット。入力と出力で共用します。"
  type        = string
}

variable "package_path" {
  description = "build.py で生成した Linux x86_64 / Python 3.13 用 Lambda ZIP のパス。"
  type        = string
}

variable "config" {
  description = "入力・出力 prefix、画質・サイズ、実行リソースの設定。prefix の変更は通知・IAM・環境変数へ一括反映します。"
  type = object({
    input_prefix         = string
    output_prefix        = string
    output_format        = string
    quality              = number
    max_width            = number
    max_height           = number
    max_input_bytes      = number
    max_input_pixels     = number
    memory_size          = number
    timeout              = number
    reserved_concurrency = number
  })

  validation {
    condition = alltrue([
      for prefix in [var.config.input_prefix, var.config.output_prefix] :
      can(regex("^[A-Za-z0-9][A-Za-z0-9/_.-]*/$", prefix)) && length(prefix) <= 512
    ])
    error_message = "prefix は英数字で始まる 512 文字以内の英数字・/・_・.・- とし、末尾を / にしてください。"
  }

  validation {
    condition = (
      !startswith(var.config.output_prefix, var.config.input_prefix) &&
      !startswith(var.config.input_prefix, var.config.output_prefix)
    )
    error_message = "再帰実行を防ぐため、入力と出力の prefix は同一または親子関係にできません。"
  }

  validation {
    condition = (
      contains(["webp", "jpeg", "png"], var.config.output_format) &&
      var.config.quality >= 1 && var.config.quality <= 95 &&
      alltrue([for value in [var.config.quality, var.config.max_width, var.config.max_height,
        var.config.max_input_bytes, var.config.max_input_pixels, var.config.memory_size,
      var.config.timeout, var.config.reserved_concurrency] : value == floor(value) && value > 0]) &&
      var.config.max_width <= 8192 && var.config.max_height <= 8192 &&
      var.config.max_input_bytes <= 100 * 1024 * 1024 &&
      var.config.max_input_pixels <= 40000000 &&
      var.config.memory_size >= 1024 && var.config.memory_size <= 10240 &&
      var.config.timeout <= 900
    )
    error_message = "形式は webp/jpeg/png、品質は 1〜95、寸法は 1〜8192、入力は最大 100 MiB / 4000 万画素、メモリは 1024〜10240 MiB、タイムアウトは 1〜900 秒、同時実行数は正の整数にしてください。"
  }
}
