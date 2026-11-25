output "function_name" {
  description = "画像圧縮 Lambda の関数名。"
  value       = aws_lambda_function.image_compression.function_name
}

output "log_group_name" {
  description = "圧縮結果・スキップ理由・実行エラーを確認するロググループ名。"
  value       = aws_cloudwatch_log_group.image_compression.name
}

output "paths" {
  description = "元画像と圧縮画像の保存先 S3 URI。"
  value = {
    input  = "s3://${var.bucket_name}/${var.config.input_prefix}"
    output = "s3://${var.bucket_name}/${var.config.output_prefix}"
  }
}
