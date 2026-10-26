"""商品レビューの投稿・編集・削除 のシリアライザー

使う view: api/views/public/reviews.py

このファイルに書くもの（リクエストの検証用・レスポンスの形用）:
  - レビュー投稿（POST /api/v1/products/:productId/reviews）: 入力の検証とレスポンス
  - レビュー編集（PATCH /api/v1/users/me/reviews/:reviewId）: 入力の検証とレスポンス
  - レビュー削除（DELETE /api/v1/users/me/reviews/:reviewId）: 入力の検証とレスポンス

入力エラーは 400（項目ごとのメッセージ）。カラム名は claude/er-diagram.md に合わせる
"""
