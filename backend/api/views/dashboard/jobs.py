"""求人管理・採用

認証: 生産者
共通: 生産者APIの共通チェック（approved でなければ 403、掲載停止中にできない操作は 409）は common/permissions.py

このファイルに書くもの（APIView / generics のクラス）。シーケンス図は Notion の同名の図:
  - 求人一覧（生産者）: GET /api/v1/dashboard/jobs
  - 求人登録: POST /api/v1/dashboard/jobs
      ・勤務日の配列も登録。long は勤務日なし、one_day・short の公開には今日以降の勤務日1日以上。画像は任意
  - 求人詳細（生産者）: GET /api/v1/dashboard/jobs/:jobId
  - 求人更新: PATCH /api/v1/dashboard/jobs/:jobId
      ・勤務日は既存分を id 付きで送り、送られなかったものは削除。希望者がいる勤務日の削除は 409
  - 求人削除: DELETE /api/v1/dashboard/jobs/:jobId
      ・応募されたことがあれば 409（非公開にしてもらう）
  - 求人応募者一覧: GET /api/v1/dashboard/jobs/:jobId/applications
      ・status で絞り込み。氏名・電話・年齢（birth_date から計算）・message・answers・希望日。生年月日とメールは返さない
  - 採用・不採用: PATCH /api/v1/dashboard/jobs/:jobId/applications/:applicationId
      ・applied→screening・hired・rejected、screening→hired・rejected、長期の hired→completed
      ・hired・rejected は戻せない。hired・rejected のときだけ応募者に通知・定型文メール
      ・募集人数を超えても採用可（超えているかを返す）

仕様: claude/api-spec.md / カラム名: claude/er-diagram.md
"""
