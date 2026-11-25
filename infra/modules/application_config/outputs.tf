output "parameter_names" {
  description = "ECS の環境変数名をキーにした Parameter Store の名前。"
  value       = { for name, parameter in aws_ssm_parameter.application : name => parameter.name }
}

output "parameter_arns" {
  description = "ECS の環境変数名をキーにしたパラメータ ARN。タスク定義と実行ロールへ渡します。"
  value       = { for name, parameter in aws_ssm_parameter.application : name => parameter.arn }
}

output "values" {
  description = "非機密の設定値だけを返します。秘密値をこの output に追加しないでください。"
  value       = local.parameter_values
}

output "revision" {
  description = "保存値が変わった際に ECS の再デプロイを起動する、非機密設定のハッシュ。"
  value       = sha256(jsonencode(local.parameter_values))

  # 値の保存が完了してから、新しいタスクが Parameter Store を読み込むようにする。
  depends_on = [aws_ssm_parameter.application]
}
