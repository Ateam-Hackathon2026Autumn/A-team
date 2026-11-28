import type { RestMock } from '../../types';
import { createJob } from '../store/dashboardJobs';

// 【生産者】求人登録API POST /api/v1/dashboard/jobs

// 求人と勤務日（workDates）をまとめて登録し、登録後の詳細（求人詳細取得APIと同じ形）を返す
// 必須: title・termType・payUnit・payAmount・workHours・workPlace・slots・description・inexperiencedOk
// 任意: prefectureId（省略時は生産者の都道府県）・periodStart・periodEnd・requirements・belongings・notes・
//   coverImage（アップロード済み画像のキー）・publishStatus（省略時は draft）・workDates
// 長期（long）は勤務日なし。単発・短期を公開するには今日以降の勤務日が1日以上必要
// 定義にない項目（例: coverImageKey）は 400。データは store/dashboardJobs.tsx

// 入力不正（status: 400）:
//   { errorCode: 'VALIDATION_ERROR', errorMsg: '入力内容に誤りがあります。', details: { title: ['この項目は必須です。'] } }
const dashboardJobCreate: RestMock = {
  method: 'POST',
  path: '/api/v1/dashboard/jobs',
  status: 201,
  handler: (_url, init) => createJob(init),
};

export { dashboardJobCreate };
