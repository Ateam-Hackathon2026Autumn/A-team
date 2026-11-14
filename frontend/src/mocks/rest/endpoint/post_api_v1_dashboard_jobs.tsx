import type { RestMock } from '../../types';
import { createJob } from '../store/dashboardJobs';

// 【生産者】求人登録API POST /api/v1/dashboard/jobs
//
// 求人と勤務日（workDates）をまとめて登録し、ID と公開状態を返す。ETag はレスポンスヘッダー
// 全項目が必須（任意の情報は null、勤務日なしは空配列）。同じ Idempotency-Key の再送は最初の結果を返す
// データは store/dashboardJobs.tsx
//
// 入力不正（status: 400）:
//   { errorCode: 'VALIDATION_ERROR', errorMsg: '入力内容に誤りがあります。', details: { title: ['入力してください。'] } }
// 公開に必要な項目が足りない（status: 409）:
//   { errorCode: 'CONFLICT', errorMsg: '公開するには、今日以降の勤務日が1日以上必要です。' }
const dashboardJobCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/jobs',
  status: 201,
  handler: (_url, init) => createJob(init),
};

export { dashboardJobCreate };
