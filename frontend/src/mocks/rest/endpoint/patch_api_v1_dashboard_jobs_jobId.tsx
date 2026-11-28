import type { RestMock } from '../../types';
import { updateJob } from '../store/dashboardJobs';

// 【生産者】求人更新API PATCH /api/v1/dashboard/jobs/{jobId}

// 送った項目だけを更新し、更新後の詳細（求人詳細取得APIと同じ形）を返す
// workDates を送ると、id 付きは更新・id なしは追加・送らなかった既存の勤務日は削除になる
// 応募があっても項目は変更できる。ただし応募者が希望している勤務日の削除・日付変更はできない
// 定義にない項目（例: coverImageKey）は 400。データは store/dashboardJobs.tsx

// 入力不正（status: 400）:
//   { errorCode: 'VALIDATION_ERROR', errorMsg: '入力内容に誤りがあります。', details: { workDates: ['長期求人には勤務日を登録できません。'] } }
// 応募者が希望している勤務日を削除・変更しようとした（status: 409）:
//   { errorCode: 'WORK_DATE_HAS_APPLICATIONS', errorMsg: '応募者が希望している勤務日は削除できません。' }
// 掲載停止中の求人の公開状態を変えようとした（status: 409）:
//   { errorCode: 'CONTENT_SUSPENDED', errorMsg: '運営により掲載停止中のため、公開状態は変更できません。' }
const dashboardJobUpdate: RestMock = {
  method: 'PATCH',
  path: '/api/v1/dashboard/jobs/:jobId',
  status: 200,
  handler: (url, init) => updateJob(url, init),
};

export { dashboardJobUpdate };
