resource "aws_lambda_permission" "uploads" {
  statement_id   = "AllowUploadsBucket"
  action         = "lambda:InvokeFunction"
  function_name  = aws_lambda_function.image_compression.function_name
  principal      = "s3.amazonaws.com"
  source_arn     = local.bucket_arn
  source_account = var.aws_account_id
}

# バケット本体は bootstrap、通知設定全体はこのリソースだけで管理します。
# 通知を追加する場合も、同じバケット用の別リソースを作らずここへまとめます。
resource "aws_s3_bucket_notification" "uploads" {
  bucket = var.bucket_name

  lambda_function {
    id                  = "compress-uploaded-images"
    lambda_function_arn = aws_lambda_function.image_compression.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = var.config.input_prefix
  }

  depends_on = [aws_lambda_permission.uploads, aws_lambda_function_event_invoke_config.image_compression]
}
