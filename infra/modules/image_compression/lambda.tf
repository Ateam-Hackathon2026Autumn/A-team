resource "aws_cloudwatch_log_group" "image_compression" {
  name              = "/aws/lambda/${var.name}"
  retention_in_days = 30
}

resource "aws_lambda_function" "image_compression" {
  function_name                  = var.name
  description                    = "画像用 S3 の指定 prefix への保存を検知し、同じバケットの別 prefix に圧縮画像を保存します。"
  role                           = aws_iam_role.image_compression.arn
  runtime                        = "python3.13"
  architectures                  = ["x86_64"]
  handler                        = "handler.lambda_handler"
  filename                       = var.package_path
  source_code_hash               = fileexists(var.package_path) ? filebase64sha256(var.package_path) : null
  memory_size                    = var.config.memory_size
  timeout                        = var.config.timeout
  reserved_concurrent_executions = var.config.reserved_concurrency

  environment {
    variables = {
      BUCKET_NAME        = var.bucket_name
      BUCKET_OWNER       = var.aws_account_id
      INPUT_PREFIX       = var.config.input_prefix
      OUTPUT_PREFIX      = var.config.output_prefix
      OUTPUT_FORMAT      = var.config.output_format
      QUALITY            = tostring(var.config.quality)
      MAX_WIDTH          = tostring(var.config.max_width)
      MAX_HEIGHT         = tostring(var.config.max_height)
      MAX_INPUT_BYTES    = tostring(var.config.max_input_bytes)
      MAX_INPUT_PIXELS   = tostring(var.config.max_input_pixels)
      PROCESSOR_REVISION = fileexists(var.package_path) ? filesha256(var.package_path) : "unbuilt"
    }
  }

  lifecycle {
    precondition {
      condition     = fileexists(var.package_path)
      error_message = "先に python3 infra/lambda/image_compression/build.py を実行して Lambda ZIP を生成してください。"
    }
  }

  # S3 と Logs のみを利用するため、VPC / NAT 接続は不要です。
  depends_on = [aws_iam_role_policy.image_compression]
}

resource "aws_lambda_function_event_invoke_config" "image_compression" {
  function_name                = aws_lambda_function.image_compression.function_name
  maximum_retry_attempts       = 2
  maximum_event_age_in_seconds = 3600
}
