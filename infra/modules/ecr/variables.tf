variable "name" {
  description = "環境名を含むリソース名の接頭辞（例: a-team-dev）。"
  type        = string
}

variable "force_delete" {
  description = "イメージを含むリポジトリの強制削除設定。bootstrap では false を維持します。削除には prevent_destroy の明示的な解除も必要です。"
  type        = bool
  default     = false
}

variable "image_tag_mutability" {
  description = "MUTABLE は同じタグでの上書きを許可し、IMMUTABLE は上書きを禁止します。"
  type        = string
  default     = "IMMUTABLE"

  validation {
    condition     = contains(["MUTABLE", "IMMUTABLE"], var.image_tag_mutability)
    error_message = "image_tag_mutability は MUTABLE または IMMUTABLE にしてください。"
  }
}
