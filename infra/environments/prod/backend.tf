# prod の state を dev と別の key で保存する。bucket・region・allowed_account_ids はローカルの backend 設定から渡す。
terraform {
  backend "s3" {
    key          = "terraform/environments/prod/terraform.tfstate"
    use_lockfile = true
  }
}
