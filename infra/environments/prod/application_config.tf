# bootstrap から受け取った画像用 S3 名と、frontend モジュールの output を設定値に使う。
# CloudFront の URL をコピーして tfvars やコンソールへ手入力する必要はない。
module "application_config" {
  source = "../../modules/application_config"

  path_prefix         = "/${var.project_name}/prod"
  uploads_bucket_name = var.uploads_bucket_name
  frontend_url        = module.frontend.url
}
